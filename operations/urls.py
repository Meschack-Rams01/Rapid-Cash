from django.urls import path
from . import views

urlpatterns = [
    path('nouveau/', views.create_operation, name='create_operation'),
    path('caisses/creer/', views.create_caisse, name='create_caisse'),
    path('<int:operation_id>/', views.operation_detail, name='operation_detail'),
    path('<int:operation_id>/supprimer/', views.delete_operation, name='delete_operation'),
    path('rapport-quotidien/apercu/', views.preview_daily_report, name='preview_daily_report'),
    path('rapport-quotidien/', views.export_daily_report_pdf, name='export_daily_report_pdf'),
    path('rapport-<str:period>/', views.export_period_report_pdf, name='export_period_report_pdf'),
    path('liste/', views.operation_list, name='operation_list'),
]
