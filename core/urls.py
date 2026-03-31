from django.urls import path
from . import views
from .views_auth import custom_logout

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Gestion de la paie
    path('paie/', views.payroll_dashboard, name='payroll_dashboard'),
    path('paie/calculer/', views.calculate_salaries, name='calculate_salaries'),
    path('paie/payer/<int:salary_id>/', views.pay_salary, name='pay_salary'),
    path('paie/bonus/<int:salary_id>/', views.add_bonus, name='add_bonus'),
    
    # Agents et utilisateurs
    path('agents/', views.agents_list, name='agents_list'),
    path('agents/creer/', views.create_agent, name='create_agent'),
    path('agents/editer/<int:agent_id>/', views.edit_agent, name='edit_agent'),
    path('agents/supprimer/<int:user_id>/', views.delete_user, name='delete_user'),
    
    # Associés et investisseurs
    path('associates/', views.associates_list, name='associates_list'),
    path('associates/creer/', views.create_associate, name='create_associate'),
    path('investors/', views.investors_list, name='investors_list'),
    path('investors/creer/', views.create_investor, name='create_investor'),
    
    # Caisses
    path('caisses/', views.caisses_list, name='caisses_list'),
    
    # Taux de change
    path('taux-change/', views.exchange_rates, name='exchange_rates'),
    
    # Profil utilisateur
    path('profil/', views.user_profile, name='user_profile'),
    
    # Authentification
    path('logout/', custom_logout, name='logout'),
]
