from django.urls import path
from . import views

urlpatterns = [
    # Dépenses (CBV)
    path('depenses/', views.ExpenseListView.as_view(), name='expense_list'),
    path('depenses/<int:expense_id>/', views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('depenses/ajouter/', views.ExpenseCreateView.as_view(), name='create_expense'),
    
    # Commissions (FBV)
    path('commissions/', views.commissions_list, name='commissions_list'),
    
    # Capital (CBV)
    path('capital/', views.CapitalTransactionListView.as_view(), name='capital_list'),
    path('capital/nouveau/', views.CapitalTransactionCreateView.as_view(), name='create_capital_transaction'),
    
    # Bénéfices (CBV)
    path('benefices/retraits/', views.ProfitWithdrawalListView.as_view(), name='profit_withdrawal_list'),
    path('benefices/retraits/nouveau/', views.ProfitWithdrawalCreateView.as_view(), name='create_profit_withdrawal'),
]
