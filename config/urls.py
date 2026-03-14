"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import dashboard_view
from core.views_auth import (
    custom_login, 
    two_factor_verify, 
    two_factor_setup, 
    two_factor_enable, 
    two_factor_disable
)
from django.shortcuts import render
from django.contrib.auth import views as auth_views
from operations import views as operations_views

# Reports view
def reports_index(request):
    from django.contrib.auth import get_user_model
    from operations.models import Operation, FeeGrid
    from finance.models import Expense
    from django.db.models import Sum
    from django.utils import timezone
    
    User = get_user_model()
    
    # Get context data
    context = {
        'period': request.GET.get('period', 'monthly'),
        'selected_agent': request.GET.get('agent', ''),
        'agents': User.objects.filter(role='AGENT') if request.user.role == 'ADMIN' else None,
        'report_data': None,
        'recent_reports': []  # TODO: Implement report history
    }
    
    # Generate report data if period is specified
    if request.GET.get('period'):
        period = request.GET.get('period')
        today = timezone.now().date()
        
        # Filter operations based on period
        operations = Operation.objects.all()
        if request.user.role != 'ADMIN':
            operations = operations.filter(agent=request.user)
        
        selected_agent_id = request.GET.get('agent')
        if selected_agent_id and request.user.role == 'ADMIN':
            operations = operations.filter(agent_id=selected_agent_id)
        
        # Apply date filter
        if period == 'daily':
            operations = operations.filter(date_time__date=today)
        elif period == 'weekly':
            week_start = today - timezone.timedelta(days=today.weekday())
            operations = operations.filter(date_time__date__gte=week_start)
        elif period == 'monthly':
            operations = operations.filter(date_time__date__year=today.year, date_time__date__month=today.month)
        elif period == 'quarterly':
            quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
            operations = operations.filter(date_time__date__gte=quarter_start)
        elif period == 'yearly':
            operations = operations.filter(date_time__date__year=today.year)
        
        # Calculate totals
        total_volume = operations.aggregate(Sum('amount_ref'))['amount_ref__sum'] or 0
        total_fees = operations.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or 0
        
        # Get expenses for the same period
        expenses = Expense.objects.all()
        if period == 'daily':
            expenses = expenses.filter(date=today)
        elif period == 'weekly':
            week_start = today - timezone.timedelta(days=today.weekday())
            expenses = expenses.filter(date__gte=week_start)
        elif period == 'monthly':
            expenses = expenses.filter(date__year=today.year, date__month=today.month)
        elif period == 'quarterly':
            quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
            expenses = expenses.filter(date__gte=quarter_start)
        elif period == 'yearly':
            expenses = expenses.filter(date__year=today.year)
        
        total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Calculate commissions
        total_commissions = 0
        if request.user.role == 'ADMIN':
            for op in operations:
                rate = op.agent.commission_rate or 0
                total_commissions += (op.fee_calculated * rate / 100)
        elif request.user.role == 'AGENT':
            rate = request.user.commission_rate or 0
            total_commissions = (total_fees * rate / 100)
        
        net_profit = total_fees - total_expenses - total_commissions
        
        context['report_data'] = {
            'total_volume': total_volume,
            'total_fees': total_fees,
            'total_expenses': total_expenses,
            'total_commissions': total_commissions,
            'net_profit': net_profit,
        }
    
    return render(request, 'reports/index.html', context)

# Settings view  
def settings_index(request):
    from operations.models import FeeGrid
    fee_grid = FeeGrid.objects.all().order_by('min_amount')
    return render(request, 'settings/index.html', {'fee_grid': fee_grid})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard_view, name='home'),
    path("dashboard/", dashboard_view, name='dashboard'),
    path("operations/", include("operations.urls")),
    path("core/", include(("core.urls", "core"), namespace="core")),
    path("finance/", include("finance.urls")),
    path("rapports/", reports_index, name='reports_index'),
    path("rapports/journalier/", operations_views.export_daily_report_pdf, name='report_daily'),
    path("rapports/exporter/", operations_views.export_daily_report_pdf, name='report_export'),
    path("parametres/", settings_index, name='settings_index'),
    
    # Custom auth URLs
    path("login/", custom_login, name="login"),
    
    # Password Reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path("logout/", lambda r: redirect('login'), name='logout'),
    
    # 2FA URLs
    path('two-factor/verify/', two_factor_verify, name='two_factor_verify'),
    path('two-factor/setup/', two_factor_setup, name='two_factor_setup'),
    path('two-factor/enable/', two_factor_enable, name='two_factor_enable'),
    path('two-factor/disable/', two_factor_disable, name='two_factor_disable'),
    
    # API endpoints
    path("api/core/", include("core.urls_api")),
    path("api/operations/", include("operations.urls_api")),
    path("api-auth/", include("rest_framework.urls", namespace='rest_framework')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
