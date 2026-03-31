from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from operations.models import Operation, Caisse
from finance.models import Expense
from django.db.models import Sum, F
from django.utils import timezone
import calendar

@login_required
def dashboard_view(request):
    user = request.user
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    
    # Base query for current MONTH (not just today)
    operations_month = Operation.objects.filter(
        date_time__month=current_month,
        date_time__year=current_year
    )
    
    # Filter for agents
    if user.role != 'ADMIN':
        operations_month = operations_month.filter(agent=user)
    
    # KPI Calculations for the MONTH
    total_volume = operations_month.aggregate(Sum('amount_ref'))['amount_ref__sum'] or 0
    total_fees = operations_month.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or 0
    total_operations = operations_month.count()
    
    # Caisse Balance
    if user.role == 'ADMIN':
        total_caisse = Caisse.objects.aggregate(Sum('balance'))['balance__sum'] or 0
        caisses = Caisse.objects.all()
    else:
        total_caisse = Caisse.objects.filter(agent=user).aggregate(Sum('balance'))['balance__sum'] or 0
        caisses = Caisse.objects.filter(agent=user)

    # Admin Specific: Expenses and Commissions for the MONTH
    total_expenses = 0
    total_commissions = 0
    net_profit = 0
    
    if user.role == 'ADMIN':
        # Total expenses for the month
        total_expenses = Expense.objects.filter(
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Calculate total commissions for all agents for the month
        for op in operations_month:
            rate = op.agent.commission_rate or 0
            total_commissions += (op.fee_calculated * rate / 100)
        
        net_profit = total_fees - total_expenses - total_commissions
    
    elif user.role == 'AGENT':
        # Personal commission for the agent
        rate = user.commission_rate or 0
        total_commissions = (total_fees * rate / 100)

    # Recent items (today only for recent activity)
    operations_today = Operation.objects.filter(date_time__date=today)
    if user.role != 'ADMIN':
        operations_today = operations_today.filter(agent=user)
    recent_operations = operations_today.order_by('-date_time')[:10]

    # Partner Data
    partner_contract = None
    partner_payments = None
    if user.role in ['ASSOCIATE', 'INVESTOR']:
        try:
            from finance.models import PartnerContract
            partner_contract = PartnerContract.objects.filter(partner=user).first()
            if partner_contract:
                partner_payments = partner_contract.payments.all().order_by('-date')
        except Exception as e:
            # Log l'erreur mais ne casse pas la vue
            print(f"Erreur lors du chargement du contrat partenaire: {e}")
            pass

    context = {
        'total_volume': total_volume,
        'total_fees': total_fees,
        'total_operations': total_operations,
        'total_caisse': total_caisse,
        'total_expenses': total_expenses,
        'total_commissions': total_commissions,
        'net_profit': net_profit,
        'recent_operations': recent_operations,
        'partner_contract': partner_contract,
        'partner_payments': partner_payments,
        'caisses': caisses,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def agents_list(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    agents = User.objects.all().order_by('role', 'username')
    
    # Get user roles for filter dropdown (as list of tuples for template)
    user_roles = [
        ('ADMIN', 'Administrateur'),
        ('AGENT', 'Agent'),
        ('ASSOCIATE', 'Associé'),
        ('INVESTOR', 'Investisseur'),
    ]
    
    context = {
        'users': agents,  # Template expects 'users'
        'user_roles': user_roles,
        'request': request,  # Add request object for template access
    }
    return render(request, 'core/agents_list.html', context)


@login_required
def delete_user(request, user_id):
    """
    Supprimer un utilisateur (Admin uniquement)
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from django.contrib.auth import get_user_model
    from django.db import transaction
    User = get_user_model()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                target_user = User.objects.get(id=user_id)
                
                # Empêcher la suppression de soi-même ou d'un autre admin
                if target_user.id == request.user.id:
                    messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
                    return redirect('core:agents_list')
                
                if target_user.role == 'ADMIN':
                    messages.error(request, "Vous ne pouvez pas supprimer un administrateur.")
                    return redirect('core:agents_list')
                
                username = target_user.username
                
                # Supprimer les références dans MonthlySalary d'abord
                from .models import MonthlySalary
                MonthlySalary.objects.filter(agent=target_user).delete()
                
                # Supprimer les opérations associées (optionnel - à décider)
                # from operations.models import Operation
                # Operation.objects.filter(agent=target_user).update(agent=None)
                
                target_user.delete()
                messages.success(request, f"L'utilisateur {username} a été supprimé avec succès.")
            
        except User.DoesNotExist:
            messages.error(request, "Utilisateur introuvable.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return redirect('core:agents_list')


@login_required
def create_agent(request):
    """
    Créer un nouvel agent (Admin uniquement)
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
        
    from .forms import AgentCreationForm
    
    if request.method == 'POST':
        form = AgentCreationForm(request.POST)
        if form.is_valid():
            agent = form.save()
            messages.success(request, f"L'agent {agent.username} a été créé avec succès.")
            
            # Log action
            from core.models import AuditLog
            AuditLog.log_action(
                user=request.user,
                action=AuditLog.ActionType.CREATE,
                model_name='User',
                object_id=str(agent.id),
                object_repr=str(agent),
                changes={'username': agent.username, 'role': 'AGENT', 'commission': str(agent.commission_rate)}
            )
            return redirect('core:agents_list')
    else:
        form = AgentCreationForm()
        
    context = {
        'form': form,
        'request': request,
    }
    return render(request, 'core/create_agent.html', context)


@login_required
def edit_agent(request, agent_id):
    """
    Éditer un agent existant (Admin uniquement)
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
        
    from django.contrib.auth import get_user_model
    from .forms import AgentEditForm
    User = get_user_model()
    
    try:
        agent = User.objects.get(id=agent_id, role='AGENT')
    except User.DoesNotExist:
        messages.error(request, "Agent introuvable.")
        return redirect('core:agents_list')
        
    if request.method == 'POST':
        form = AgentEditForm(request.POST, instance=agent)
        if form.is_valid():
            old_commission = agent.commission_rate
            agent = form.save()
            messages.success(request, f"Les informations de {agent.username} ont été mises à jour.")
            
            # Log action
            from core.models import AuditLog
            AuditLog.log_action(
                user=request.user,
                action=AuditLog.ActionType.UPDATE,
                model_name='User',
                object_id=str(agent.id),
                object_repr=str(agent),
                changes={
                    'username': agent.username, 
                    'commission_rate': [str(old_commission), str(agent.commission_rate)],
                    'is_active': agent.is_active
                }
            )
            return redirect('core:agents_list')
    else:
        form = AgentEditForm(instance=agent)
        
    context = {
        'form': form,
        'agent': agent,
        'request': request,
    }
    return render(request, 'core/edit_agent.html', context)


@login_required
def caisses_list(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    caisses = Caisse.objects.all().order_by('name')
    
    # Calculate total balance
    total_balance = sum(c.balance for c in caisses)
    base_currency = 'USD'  # Default
    
    context = {
        'caisses': caisses,
        'total_balance': total_balance,
        'base_currency': base_currency,
        'request': request,  # Add request object for template access
    }
    return render(request, 'core/caisses_list.html', context)

@login_required
def associates_list(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from django.contrib.auth import get_user_model
    from finance.models import PartnerContract
    from core.models import Currency
    User = get_user_model()
    
    associates = User.objects.filter(role='ASSOCIATE').select_related('contract')
    
    from decimal import Decimal
    # Calculate totals
    total_engaged = sum(
        (c.amount_engaged or Decimal('0')) for c in PartnerContract.objects.filter(type='ASSOCIATE')
    ) or Decimal('0')
    total_expected_return = sum(
        (c.expected_return_percent or Decimal('0')) for c in PartnerContract.objects.filter(type='ASSOCIATE')
    ) / max(PartnerContract.objects.filter(type='ASSOCIATE').count(), 1) if PartnerContract.objects.filter(type='ASSOCIATE').exists() else Decimal('0')
    
    context = {
        'associates': associates,
        'total_engaged': total_engaged,
        'total_expected_return': total_expected_return,
        'request': request,  # Add request object for template access
        'currencies': Currency.objects.all(),  # Add currencies for form
    }
    return render(request, 'core/associates_list.html', context)

@login_required
def investors_list(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from django.contrib.auth import get_user_model
    from finance.models import PartnerContract
    from core.models import Currency
    from django.db.models import Sum
    from django.db.models.functions import Coalesce
    from django.db.models import DecimalField
    User = get_user_model()
    
    investors = User.objects.filter(role='INVESTOR').select_related('contract')
    
    from decimal import Decimal
    # Calculate totals
    contracts = PartnerContract.objects.filter(type='INVESTOR')
    total_invested = sum((c.amount_engaged or Decimal('0')) for c in contracts) or Decimal('0')
    
    # Calculate total returns from payments
    total_returns = sum(
        (payment['total'] or Decimal('0')) 
        for payment in contracts.annotate(
            total=Coalesce(Sum('payments__amount'), 0, output_field=DecimalField())
        ).values('total')
    ) or Decimal('0')
    
    pending_payments = total_invested - total_returns
    
    context = {
        'investors': investors,
        'total_invested': total_invested,
        'total_returns': total_returns,
        'pending_payments': pending_payments,
        'request': request,  # Add request object for template access
        'currencies': Currency.objects.all(),  # Add currencies for form
    }
    return render(request, 'core/investors_list.html', context)

@login_required
def create_associate(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .forms import AssociateForm
    from django.http import JsonResponse
    
    if request.method == 'POST':
        form = AssociateForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Associé créé avec succès'})
                messages.success(request, "Associé créé avec succès.")
                return redirect('core:associates_list')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Erreur: {str(e)}")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, field_errors in form.errors.items():
                    errors[field] = field_errors[0] if field_errors else 'Erreur de validation'
                return JsonResponse({'success': False, 'error': 'Veuillez vérifier les champs', 'errors': errors})
    else:
        form = AssociateForm()
    
    return render(request, 'core/create_associate.html', {'form': form})

@login_required
def create_investor(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .forms import InvestorForm
    from django.http import JsonResponse
    
    if request.method == 'POST':
        form = InvestorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Investisseur créé avec succès'})
                messages.success(request, "Investisseur créé avec succès.")
                return redirect('core:investors_list')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f"Erreur: {str(e)}")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, field_errors in form.errors.items():
                    errors[field] = field_errors[0] if field_errors else 'Erreur de validation'
                return JsonResponse({'success': False, 'error': 'Veuillez vérifier les champs', 'errors': errors})
    else:
        form = InvestorForm()
    
    return render(request, 'core/create_investor.html', {'form': form})

@login_required
def exchange_rates(request):
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from core.models import Currency, ExchangeRate
    from django.db import transaction
    
    # Handle POST requests for adding/editing rates
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            base_id = request.POST.get('base_currency')
            target_id = request.POST.get('target_currency')
            rate_value = request.POST.get('rate')
            
            try:
                base_currency = Currency.objects.get(id=base_id)
                target_currency = Currency.objects.get(id=target_id)
                from decimal import Decimal
                rate = Decimal(str(rate_value))
                
                if rate <= 0:
                    messages.error(request, "Le taux doit être positif.")
                elif base_currency.id == target_currency.id:
                    messages.error(request, "Les devises source et cible doivent être différentes.")
                else:
                    # Check if rate already exists
                    existing = ExchangeRate.objects.filter(
                        base_currency=base_currency,
                        target_currency=target_currency
                    ).first()
                    
                    if existing:
                        existing.rate = rate
                        existing.save()
                        messages.success(request, f"Taux {base_currency.code} → {target_currency.code} mis à jour.")
                    else:
                        ExchangeRate.objects.create(
                            base_currency=base_currency,
                            target_currency=target_currency,
                            rate=rate
                        )
                        messages.success(request, f"Taux {base_currency.code} → {target_currency.code} créé.")
                        
                    # Log the action
                    from core.models import AuditLog
                    AuditLog.log_action(
                        user=request.user,
                        action=AuditLog.ActionType.EXCHANGE_RATE,
                        model_name='ExchangeRate',
                        object_repr=f"{base_currency.code} → {target_currency.code}: {rate}",
                        changes={'rate': rate, 'base': base_currency.code, 'target': target_currency.code}
                    )
                    
            except Currency.DoesNotExist:
                messages.error(request, "Devise introuvable.")
            except ValueError:
                messages.error(request, "Taux invalide.")
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
                
        elif action == 'edit':
            rate_id = request.POST.get('rate_id')
            new_rate = request.POST.get('rate')
            
            try:
                exchange_rate = ExchangeRate.objects.get(id=rate_id)
                from decimal import Decimal
                old_rate = exchange_rate.rate
                new_rate_float = Decimal(str(new_rate))
                
                if new_rate_float <= 0:
                    messages.error(request, "Le taux doit être positif.")
                else:
                    exchange_rate.rate = new_rate_float
                    exchange_rate.save()
                    messages.success(
                        request, 
                        f"Taux {exchange_rate.base_currency.code} → {exchange_rate.target_currency.code} mis à jour: {old_rate:.6f} → {new_rate_float:.6f}"
                    )
                    
                    # Log the action
                    from core.models import AuditLog
                    AuditLog.log_action(
                        user=request.user,
                        action=AuditLog.ActionType.UPDATE,
                        model_name='ExchangeRate',
                        object_id=str(rate_id),
                        object_repr=str(exchange_rate),
                        changes={'rate': [str(old_rate), str(new_rate_float)]}
                    )
                    
            except ExchangeRate.DoesNotExist:
                messages.error(request, "Taux introuvable.")
            except ValueError:
                messages.error(request, "Taux invalide.")
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
        
        elif action == 'update_all':
            # Auto-generate missing rates based on USD reference
            try:
                usd = Currency.objects.filter(code='USD').first()
                if not usd:
                    messages.error(request, "Devise USD (référence) non trouvée.")
                else:
                    currencies = Currency.objects.all()
                    created_count = 0
                    
                    with transaction.atomic():
                        for base in currencies:
                            for target in currencies:
                                if base.id != target.id:
                                    # Check if rate exists
                                    if not ExchangeRate.objects.filter(
                                        base_currency=base,
                                        target_currency=target
                                    ).exists():
                                        # Create a placeholder rate (1.0 for same currency pairs)
                                        ExchangeRate.objects.create(
                                            base_currency=base,
                                            target_currency=target,
                                            rate=1.0  # Default rate - should be updated with real values
                                        )
                                        created_count += 1
                    
                    if created_count > 0:
                        messages.success(request, f"{created_count} taux créés. Veuillez les mettre à jour avec les valeurs réelles.")
                    else:
                        messages.info(request, "Tous les taux existent déjà.")
                        
            except Exception as e:
                messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
        
        return redirect('core:exchange_rates')
    
    currencies = Currency.objects.all().order_by('code')
    exchange_rates_list = ExchangeRate.objects.select_related('base_currency', 'target_currency').order_by('base_currency', 'target_currency')
    
    last_update = exchange_rates_list.first().date_updated if exchange_rates_list else None
    
    context = {
        'currencies': currencies,
        'exchange_rates': exchange_rates_list,
        'last_update': last_update,
        'request': request,
    }
    return render(request, 'core/exchange_rates.html', context)

@login_required
def user_profile(request):
    """Vue pour le profil utilisateur"""
    from .forms import UserProfileForm
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès!")
            return redirect('core:user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'core/user_profile.html', {
        'form': form,
        'user': request.user
    })





# ====== GESTION DE LA PAIE ======

@login_required
def payroll_dashboard(request):
    """
    Tableau de bord de la paie mensuelle
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .models import PayPeriod, MonthlySalary
    from django.db.models import Sum
    import calendar
    
    current_date = timezone.now()
    
    # Période actuelle
    current_period, created = PayPeriod.objects.get_or_create(
        month=current_date.month,
        year=current_date.year,
        defaults={
            'start_date': current_date.replace(day=1),
            'end_date': current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1]),
            'status': 'OPEN'
        }
    )
    
    # Calculer les financiers de la période (bénéfices nets, réserves, etc)
    if created or current_period.total_fees == 0:
        current_period.calculate_financials()
    
    # Salaires du mois
    salaries = MonthlySalary.objects.filter(
        pay_period=current_period
    ).select_related('agent')
    
    # Statistiques
    total_salaries = salaries.aggregate(
        total=Sum('total_salary')
    )['total'] or 0
    
    total_paid = salaries.aggregate(
        total=Sum('paid_amount')
    )['total'] or 0
    
    pending_payment = total_salaries - total_paid
    
    # Notification si paiement dû
    payment_warning = None
    if current_period.is_payment_due():
        payment_warning = f"La date de paie est arrivée ! {pending_payment:.2f}$ à payer."
    elif current_period.days_until_payment() and current_period.days_until_payment() <= 2:
        payment_warning = f"Attention : Paie dans {current_period.days_until_payment()} jours !"
    
    context = {
        'period': current_period,
        'salaries': salaries,
        'total_salaries': total_salaries,
        'total_paid': total_paid,
        'pending_payment': pending_payment,
        'payment_warning': payment_warning,
        'request': request,
    }
    
    return render(request, 'core/payroll_dashboard.html', context)


@login_required
def calculate_salaries(request):
    """
    Calculer automatiquement les salaires pour la période actuelle
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .models import PayPeriod, MonthlySalary
    from django.contrib.auth import get_user_model
    
    current_date = timezone.now()
    current_period, _ = PayPeriod.objects.get_or_create(
        month=current_date.month,
        year=current_date.year
    )
    
    # Recalculer les financiers de la période
    current_period.calculate_financials()
    
    # Calculer les salaires pour tous les agents
    User = get_user_model()
    agents = User.objects.filter(role='AGENT')
    
    for agent in agents:
        salary, created = MonthlySalary.objects.get_or_create(
            pay_period=current_period,
            agent=agent,
            defaults={'commission_percentage': agent.commission_rate}
        )
        
        # Recalculer le salaire
        salary.calculate_salary()
    
    # Mettre à jour le total des salaires
    current_period.total_salaries = current_period.get_salaries_total()
    current_period.save()
    
    messages.success(request, f"Salaires calculés pour {agents.count()} agent(s) !")
    return redirect('core:payroll_dashboard')


@login_required
def pay_salary(request, salary_id):
    """
    Payer un salaire (en espèces)
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .models import MonthlySalary
    
    salary = MonthlySalary.objects.get(id=salary_id)
    
    if request.method == 'POST':
        payment_amount = request.POST.get('payment_amount')
        notes = request.POST.get('notes', 'Payé en espèces')
        
        try:
            from decimal import Decimal
            payment_amount = Decimal(str(payment_amount))
            if payment_amount <= 0:
                raise ValueError("Le montant doit être positif")
            
            if payment_amount >= salary.get_remaining_amount():
                # Paiement complet
                salary.mark_as_paid(payment_amount, notes)
                messages.success(request, f"Salaire de {salary.agent.username} payé complètement !")
            else:
                # Paiement partiel
                salary.mark_partial_payment(payment_amount, notes)
                messages.success(request, f"Paiement partiel de {payment_amount}$ enregistré pour {salary.agent.username}")
                
        except (ValueError, TypeError) as e:
            messages.error(request, f"Erreur: {e}")
        
        return redirect('core:payroll_dashboard')
    
    context = {
        'salary': salary,
        'remaining_amount': salary.get_remaining_amount(),
        'request': request,
    }
    
    return render(request, 'core/pay_salary.html', context)


@login_required
def add_bonus(request, salary_id):
    """
    Ajouter un bonus à un agent
    """
    if request.user.role != 'ADMIN':
        return redirect('core:dashboard')
    
    from .models import MonthlySalary
    
    salary = MonthlySalary.objects.get(id=salary_id)
    
    if request.method == 'POST':
        bonus_amount = request.POST.get('bonus_amount')
        notes = request.POST.get('notes', 'Bonus exceptionnel')
        
        try:
            from decimal import Decimal
            bonus_amount = Decimal(str(bonus_amount))
            if bonus_amount <= 0:
                raise ValueError("Le bonus doit être positif")
            
            salary.bonus_amount += bonus_amount
            salary.calculate_salary()  # Recalculer le total
            salary.payment_notes = f"{salary.payment_notes}\nBonus: {bonus_amount}$ - {notes}".strip()
            salary.save()
            
            messages.success(request, f"Bonus de {bonus_amount}$ ajouté pour {salary.agent.username} !")
            
        except (ValueError, TypeError) as e:
            messages.error(request, f"Erreur: {e}")
        
        return redirect('core:payroll_dashboard')
    
    context = {
        'salary': salary,
        'request': request,
    }
    
    return render(request, 'core/add_bonus.html', context)
