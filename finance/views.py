from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Expense
from .forms import ExpenseForm
from django.db.models import Sum
from django.contrib.auth import get_user_model

@login_required
def expense_list(request):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')
    
    expenses = Expense.objects.select_related('admin', 'currency').order_by('-date')
    expense_categories = Expense.objects.values_list('category', flat=True).distinct()
    
    
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if category_filter:
        expenses = expenses.filter(category=category_filter)
    
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    context = {
        'expenses': expenses,
        'expense_categories': expense_categories,
        'request': request,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'finance/partials/expense_table.html', context)
        
    return render(request, 'finance/expense_list.html', context)

@login_required
def create_expense(request):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.admin = request.user
            expense.save()
            messages.success(request, "Dépense enregistrée avec succès.")
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    
    return render(request, 'finance/create_expense.html', {'form': form})

@login_required
def expense_detail(request, expense_id):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')
    
    try:
        expense = Expense.objects.select_related('admin', 'currency').get(id=expense_id)
        return render(request, 'finance/expense_detail.html', {'expense': expense})
    except Expense.DoesNotExist:
        messages.error(request, "Dépense non trouvée.")
        return redirect('expense_list')

@login_required
def commissions_list(request):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')
    
    from operations.models import Operation
    from django.db.models import F
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    User = get_user_model()
    
    # Get date filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_agent = request.GET.get('agent')
    
    # Base query
    operations = Operation.objects.select_related('agent', 'caisse').order_by('-date_time')
    
    if date_from:
        operations = operations.filter(date_time__date__gte=date_from)
    if date_to:
        operations = operations.filter(date_time__date__lte=date_to)
    if selected_agent:
        operations = operations.filter(agent_id=selected_agent)
    
    # Calculate commissions from operations
    commissions = []
    total_commissions = 0
    
    for op in operations:
        if op.agent and op.agent.commission_rate:
            comm_amount = (op.fee_calculated * (op.agent.commission_rate or Decimal('0'))) / Decimal('100')
            if comm_amount > 0:
                commissions.append({
                    'date': op.date_time,
                    'agent': op.agent,
                    'operation': op,
                    'amount': comm_amount
                })
                total_commissions += comm_amount
    
    # Get all agents for filter
    agents = User.objects.filter(role='AGENT')
    
    # Calculate totals
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_ops = Operation.objects.filter(date_time__gte=month_start)
    monthly_commissions = sum(
        (op.fee_calculated * (op.agent.commission_rate or Decimal('0'))) / Decimal('100')
        for op in monthly_ops.select_related('agent')
        if op.agent and op.agent.commission_rate
    ) or Decimal('0')
    
    context = {
        'commissions': commissions,
        'agents': agents,
        'total_commissions': total_commissions,
        'monthly_commissions': monthly_commissions,
        'active_agents': agents.filter(is_active=True).count(),
        'average_rate': sum((a.commission_rate or Decimal('0')) for a in agents) / max(agents.count(), 1) if agents.exists() else Decimal('0'),
        'total_period': total_commissions,
        'request': request,  # Add request object for template access
    }
    return render(request, 'finance/commissions_list.html', context)
