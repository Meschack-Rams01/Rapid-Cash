from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

class AdminRequiredMixin(AccessMixin):
    """
    Mixin that requires the user to be authenticated and have the 'ADMIN' role.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'ADMIN':
            messages.error(request, "Accès refusé. Réservé aux administrateurs.")
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class AdminCreateMixin:
    """
    Mixin for CreateView that automatically assigns the current admin user 
    to the 'admin' field of the model upon form validation.
    """
    def form_valid(self, form):
        form.instance.admin = self.request.user
        messages.success(self.request, getattr(self, 'success_message', "Opération enregistrée avec succès."))
        return super().form_valid(form)


class DateFilterMixin:
    """
    Mixin for ListView to automatically filter querysets by 'date_from' and 'date_to'
    GET parameters. Expects the model to have a date/datetime field defined by `date_filter_field`.
    """
    date_filter_field = 'date_time'  # Default field name, can be overridden in view
    
    def get_queryset(self):
        queryset = super().get_queryset()
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            filter_kwargs = {f"{self.date_filter_field}__date__gte": date_from}
            # Special case for 'date' fields without datetime
            if self.date_filter_field == 'date':
                filter_kwargs = {f"{self.date_filter_field}__gte": date_from}
            queryset = queryset.filter(**filter_kwargs)
            
        if date_to:
            filter_kwargs = {f"{self.date_filter_field}__date__lte": date_to}
            if self.date_filter_field == 'date':
                filter_kwargs = {f"{self.date_filter_field}__lte": date_to}
            queryset = queryset.filter(**filter_kwargs)
            
        return queryset
