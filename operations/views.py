from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from .forms import OperationForm
from .models import Operation, Caisse
from .services import OperationService
from core.utils.pdf import generate_pdf
from django.contrib.auth import get_user_model
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from core.mixins import AdminRequiredMixin, DateFilterMixin, AdminCreateMixin

User = get_user_model()

@login_required
def create_operation(request):
    from operations.models import FeeGrid
    from core.models import Currency
    
    # Check if agent has a caisse assigned
    if request.user.role != 'ADMIN':
        agent_caisse = Caisse.objects.filter(agent=request.user).first()
        if not agent_caisse:
            messages.error(request, "Aucune caisse assignée. Veuillez contacter l'administrateur.")
            return redirect('dashboard')
    
    # Get fee grids for display
    fee_grids = FeeGrid.objects.filter(currency__code='USD').order_by('min_amount')
    currencies = Currency.objects.all()
    
    if request.method == 'POST':
        form = OperationForm(request.POST, agent=request.user)
        if form.is_valid():
            try:
                # Get agent's caisse (for ADMIN, use first available)
                if request.user.role == 'ADMIN':
                    agent_caisse = Caisse.objects.first()
                else:
                    agent_caisse = Caisse.objects.filter(agent=request.user).first()
                
                if not agent_caisse:
                    messages.error(request, "Aucune caisse assignée. Veuillez contacter l'administrateur.")
                    context = {
                        'form': form,
                        'fee_grids': fee_grids,
                        'currencies': currencies,
                        'agent_caisse': None
                    }
                    return render(request, 'operations/create_operation.html', context)
                
                from django.db import transaction
                
                # Check if conversion was done in the form
                amount_to_use = form.cleaned_data['amount_orig']
                currency_to_use = form.cleaned_data['currency_orig']
                
                # If converted amount exists, use it for the operation
                if hasattr(form, 'converted_amount') and form.converted_amount:
                    amount_to_use = form.converted_amount
                    currency_to_use = form.converted_currency
                    messages.info(
                        request, 
                        f"Conversion appliquée: {form.cleaned_data['amount_orig']} {form.cleaned_data['currency_orig'].code} = "
                        f"{amount_to_use:.2f} {currency_to_use.code} (taux: {form.exchange_rate_used:.6f})"
                    )
                
                with transaction.atomic():
                    OperationService.create_operation(
                        agent=request.user,
                        op_type=form.cleaned_data['type'],
                        caisse_id=agent_caisse.id,
                        amount_orig=amount_to_use,
                        currency_orig_id=currency_to_use.id,
                        observation=form.cleaned_data.get('observation', "")
                    )
                messages.success(request, "Opération enregistrée avec succès!")
                return redirect('dashboard')
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Erreur: {str(e)}")
        else:
            # Form is invalid - show errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = OperationForm(agent=request.user)
    
    # Get agent's caisse for display (ADMIN uses first available)
    if request.user.role == 'ADMIN':
        agent_caisse = Caisse.objects.first()
    else:
        agent_caisse = Caisse.objects.filter(agent=request.user).first()
    
    return render(request, 'operations/create_operation.html', {
        'form': form,
        'fee_grids': fee_grids,
        'currencies': currencies,
        'agent_caisse': agent_caisse
    })

@login_required
def preview_daily_report(request):
    user = request.user
    today = timezone.now().date()
    
    operations_today = Operation.objects.filter(date_time__date=today)
    if user.role != 'ADMIN':
        operations_today = operations_today.filter(agent=user)
    
    total_volume = operations_today.aggregate(Sum('amount_ref'))['amount_ref__sum'] or 0
    total_fees = operations_today.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or 0
    count_trx = operations_today.count()

    context = {
        'today': today,
        'agent_name': user.username,
        'operations': operations_today.order_by('date_time'),
        'total_volume': total_volume,
        'total_fees': total_fees,
        'count_trx': count_trx,
        'preview': True,  # Indicateur pour l'aperçu
    }
    
    return render(request, 'reports/report_daily.html', context)

@login_required
def export_daily_report_pdf(request):
    user = request.user
    today = timezone.now().date()
    
    operations_today = Operation.objects.filter(date_time__date=today)
    if user.role != 'ADMIN':
        operations_today = operations_today.filter(agent=user)
    
    total_volume = operations_today.aggregate(Sum('amount_ref'))['amount_ref__sum'] or 0
    total_fees = operations_today.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or 0
    count_trx = operations_today.count()

    context = {
        'today': today,
        'agent_name': user.username,
        'operations': operations_today.order_by('date_time'),
        'total_volume': total_volume,
        'total_fees': total_fees,
        'count_trx': count_trx,
    }
    
    try:
        pdf = generate_pdf('reports/report_daily.html', context)
    except RuntimeError as e:
        messages.error(request, str(e))
        return redirect('dashboard')
    
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Rapport_Journalier_{today}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def export_period_report_pdf(request, period):
    user = request.user
    from django.utils import timezone
    from datetime import timedelta, date
    
    # Calculate date range based on period
    today = timezone.now().date()
    
    if period == 'weekly':
        start_date = today - timedelta(days=7)
        period_name = "Hebdomadaire"
    elif period == 'monthly':
        start_date = today.replace(day=1)
        period_name = "Mensuel"
    elif period == 'quarterly':
        # Get first day of current quarter
        month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=month, day=1)
        period_name = "Trimestriel"
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        period_name = "Annuel"
    else:
        start_date = today
        period_name = "Journalier"
    
    # Filter operations for the period
    operations = Operation.objects.filter(date_time__date__gte=start_date, date_time__date__lte=today)
    if user.role != 'ADMIN':
        operations = operations.filter(agent=user)
    
    total_volume = operations.aggregate(Sum('amount_ref'))['amount_ref__sum'] or 0
    total_fees = operations.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or 0
    count_trx = operations.count()

    context = {
        'period': period_name,
        'start_date': start_date,
        'end_date': today,
        'agent_name': user.username,
        'operations': operations.order_by('date_time'),
        'total_volume': total_volume,
        'total_fees': total_fees,
        'count_trx': count_trx,
    }
    
    try:
        pdf = generate_pdf('reports/report_period.html', context)
    except RuntimeError as e:
        messages.error(request, str(e))
        return redirect('dashboard')
    
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"Rapport_{period_name}_{today}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def operation_list(request):
    user = request.user
    queryset = Operation.objects.all()
    
    # Filter for agents
    if user.role != 'ADMIN':
        queryset = queryset.filter(agent=user)
    
    # Advanced Filtering (Admin only or Agent on their own)
    agent_id = request.GET.get('agent')
    op_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user.role == 'ADMIN' and agent_id:
        queryset = queryset.filter(agent_id=agent_id)
    
    if op_type:
        queryset = queryset.filter(type=op_type)
        
    if date_from:
        queryset = queryset.filter(date_time__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date_time__date__lte=date_to)

    # Use select_related for better performance and handle null relations
    queryset = queryset.select_related('agent', 'caisse', 'currency_orig', 'currency_ref')

    # Check if agent has a caisse assigned (for business logic validation)
    agent_has_caisse = True
    if user.role != 'ADMIN':
        agent_has_caisse = Caisse.objects.filter(agent=user).exists()
        # If agent has no caisse, they should see no operations even if they exist
        if not agent_has_caisse:
            queryset = Operation.objects.none()

    context = {
        'operations': queryset.order_by('-date_time'),
        'agents': User.objects.filter(role='AGENT') if user.role == 'ADMIN' else None,
        'types': Operation.Type.choices,
        'request': request,  # Add request object for template access
        'agent_has_caisse': agent_has_caisse,  # Pass this info to template
    }
    return render(request, 'operations/operation_list.html', context)

@login_required
def operation_detail(request, operation_id):
    user = request.user
    try:
        operation = Operation.objects.select_related('agent', 'caisse', 'currency_orig', 'currency_ref').get(id=operation_id)
        
        # Check permissions - admin can see all, agents only their own
        if user.role != 'ADMIN' and operation.agent != user:
            messages.error(request, "Vous n'avez pas la permission de voir cette opération.")
            return redirect('operation_list')
            
        return render(request, 'operations/operation_detail.html', {'operation': operation})
    except Operation.DoesNotExist:
        messages.error(request, "Opération non trouvée.")
        return redirect('operation_list')


@login_required
def delete_operation(request, operation_id):
    """
    Supprimer une opération (Admin uniquement)
    """
    if request.user.role != 'ADMIN':
        messages.error(request, "Vous n'avez pas la permission de supprimer des opérations.")
        return redirect('operation_list')
    
    if request.method == 'POST':
        try:
            operation = Operation.objects.get(id=operation_id)
            transaction_number = operation.transaction_number
            
            # Restaurer le solde de la caisse avant suppression
            caisse = operation.caisse
            if caisse:
                if operation.type == 'WITHDRAWAL':
                    # Pour un retrait, on avait diminué le solde, donc on l'augmente
                    caisse.balance += (operation.amount_orig + operation.fee_calculated)
                elif operation.type == 'TRANSFER':
                    # Pour un transfert, on avait augmenté le solde, donc on le diminue
                    caisse.balance -= (operation.amount_orig + operation.fee_calculated)
                caisse.save()
            
            operation.delete()
            messages.success(request, f"L'opération {transaction_number} a été supprimée avec succès.")
            
        except Operation.DoesNotExist:
            messages.error(request, "Opération introuvable.")
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
    
    return redirect('operation_list')


class CaisseCreateView(AdminRequiredMixin, CreateView):
    """
    Créer une nouvelle caisse (Admin uniquement)
    """
    from .forms import CaisseForm
    model = Caisse
    template_name = 'operations/create_caisse.html'
    form_class = CaisseForm
    success_url = reverse_lazy('core:caisses_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        caisse = self.object
        from django.contrib import messages
        messages.success(self.request, f"La caisse '{caisse.name}' a été créée avec succès.")
        
        from core.models import AuditLog
        AuditLog.log_action(
            user=self.request.user,
            action=AuditLog.ActionType.CREATE,
            model_name='Caisse',
            object_id=str(caisse.id),
            object_repr=str(caisse),
            changes={
                'name': caisse.name, 
                'currency': caisse.currency.code,
                'agent': caisse.agent.username if caisse.agent else None
            }
        )
        return response

class FondAllocationListView(AdminRequiredMixin, DateFilterMixin, ListView):
    """
    List of fund allocations (Admin only)
    """
    from .models import FondAllocation
    model = FondAllocation
    template_name = 'operations/allocation_list.html'
    context_object_name = 'allocations'

    def get_queryset(self):
        from .models import FondAllocation
        queryset = super().get_queryset().select_related('admin', 'agent', 'currency').order_by('-date_time')
        agent_id = self.request.GET.get('agent')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agents'] = User.objects.filter(role='AGENT')
        return context


class FondAllocationCreateView(AdminRequiredMixin, AdminCreateMixin, CreateView):
    """
    Create a fund allocation (Admin only)
    """
    from .models import FondAllocation
    from .forms import FondAllocationForm
    model = FondAllocation
    form_class = FondAllocationForm
    template_name = 'operations/create_allocation.html'
    success_url = reverse_lazy('allocation_list')

    def form_valid(self, form):
        self.success_message = f"L'allocation a été enregistrée avec succès pour l'agent {form.instance.agent.username}."
        return super().form_valid(form)
