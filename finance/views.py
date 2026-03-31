from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy

from .models import Expense, CapitalTransaction, ProfitWithdrawal
from .forms import ExpenseForm, CapitalTransactionForm, ProfitWithdrawalForm
from core.mixins import AdminRequiredMixin, DateFilterMixin, AdminCreateMixin
from django.db.models import Sum
from django.contrib.auth import get_user_model

# --- EXPENSES ---

class ExpenseListView(AdminRequiredMixin, DateFilterMixin, ListView):
    model = Expense
    template_name = 'finance/expense_list.html'
    context_object_name = 'expenses'
    date_filter_field = 'date'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('admin', 'currency').order_by('-date')
        category_filter = self.request.GET.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['expense_categories'] = Expense.objects.values_list('category', flat=True).distinct()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'finance/partials/expense_table.html', context)
        return super().render_to_response(context, **response_kwargs)


class ExpenseCreateView(AdminRequiredMixin, AdminCreateMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/create_expense.html'
    success_url = reverse_lazy('expense_list')
    success_message = "Dépense enregistrée avec succès."


class ExpenseDetailView(AdminRequiredMixin, DetailView):
    model = Expense
    template_name = 'finance/expense_detail.html'
    context_object_name = 'expense'
    pk_url_kwarg = 'expense_id'

    def get_queryset(self):
        return super().get_queryset().select_related('admin', 'currency')


# --- CAPITAL TRANSACTIONS ---

class CapitalTransactionListView(AdminRequiredMixin, DateFilterMixin, ListView):
    model = CapitalTransaction
    template_name = 'finance/capital_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('admin', 'currency').order_by('-date_time')
        txn_type = self.request.GET.get('type')
        if txn_type:
            queryset = queryset.filter(type=txn_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types'] = CapitalTransaction.Type.choices
        return context


class CapitalTransactionCreateView(AdminRequiredMixin, AdminCreateMixin, CreateView):
    model = CapitalTransaction
    form_class = CapitalTransactionForm
    template_name = 'finance/create_capital_transaction.html'
    # Use standard success_url or lazy reverse based on namespace behavior
    success_url = reverse_lazy('capital_list')  # Will fix namespace if required in urls.py

    def form_valid(self, form):
        self.success_message = f"Transaction de capital ({form.instance.get_type_display()}) enregistrée avec succès."
        return super().form_valid(form)


# --- PROFIT WITHDRAWALS ---

class ProfitWithdrawalListView(AdminRequiredMixin, DateFilterMixin, ListView):
    model = ProfitWithdrawal
    template_name = 'finance/profit_withdrawal_list.html'
    context_object_name = 'withdrawals'

    def get_queryset(self):
        return super().get_queryset().select_related('admin', 'currency').order_by('-date_time')


class ProfitWithdrawalCreateView(AdminRequiredMixin, AdminCreateMixin, CreateView):
    model = ProfitWithdrawal
    form_class = ProfitWithdrawalForm
    template_name = 'finance/create_profit_withdrawal.html'
    success_url = reverse_lazy('profit_withdrawal_list')
    success_message = "Le retrait de bénéfices a été enregistré avec succès."


# --- COMMISSIONS (Left as FBV or manual TemplateView due to complex non-ORM logic) ---

@login_required
def commissions_list(request):
    if request.user.role != 'ADMIN':
        return redirect('dashboard')
    
    from operations.models import Operation
    from decimal import Decimal
    from django.utils import timezone
    User = get_user_model()
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_agent = request.GET.get('agent')
    
    operations = Operation.objects.select_related('agent', 'caisse').order_by('-date_time')
    
    if date_from:
        operations = operations.filter(date_time__date__gte=date_from)
    if date_to:
        operations = operations.filter(date_time__date__lte=date_to)
    if selected_agent:
        operations = operations.filter(agent_id=selected_agent)
    
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
    
    agents = User.objects.filter(role='AGENT')
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
    }
    return render(request, 'finance/commissions_list.html', context)
