"""
Rapid Cash - Operations Service
Automatic fee calculation based on fee grid
"""
from decimal import Decimal
from django.db.models import Sum, Count
from django.core.exceptions import ValidationError
from operations.models import FeeGrid, Operation, Caisse
from finance.models import Expense
from core.models import Currency, AuditLog


class OperationService:
    """
    Service class for handling operations.
    According to specification sections 4, 9, 10.
    """
    
    @staticmethod
    def create_operation(agent, op_type, caisse_id, amount_orig, currency_orig_id, observation=''):
        """
        Create a new operation with automatic fee calculation.
        
        Args:
            agent: User object (agent)
            op_type: Type of operation (TRANSFER/WITHDRAWAL)
            caisse_id: ID of the caisse
            amount_orig: Original amount
            currency_orig_id: ID of the original currency
            observation: Optional observation
            
        Returns:
            Operation: Created operation object
            
        Raises:
            ValidationError: If validation fails
        """
        from django.utils import timezone
        import uuid
        
        # Get currency
        currency_orig = Currency.objects.get(id=currency_orig_id)
        
        # Get reference currency (USD)
        try:
            currency_ref = Currency.objects.get(is_reference=True)
        except Currency.DoesNotExist:
            currency_ref = currency_orig
        
        # Get exchange rate (1 if same currency)
        exchange_rate = Decimal('1')
        if currency_orig != currency_ref:
            try:
                # Fetch from ExchangeRate model
                from core.models import ExchangeRate
                rate_obj = ExchangeRate.objects.filter(
                    base_currency=currency_orig,
                    target_currency=currency_ref
                ).first()
                if rate_obj:
                    exchange_rate = rate_obj.rate
                else:
                    raise ValidationError(f"No exchange rate found for {currency_orig.code} to {currency_ref.code}")
            except Exception as e:
                raise ValidationError(f"Exchange rate error: {str(e)}")
        
        # Convert amount to reference currency
        amount_ref = amount_orig * exchange_rate
        
        # Calculate automatic fee based on fee grid
        fee = OperationService._calculate_fee(amount_ref, currency_ref)
        
        # Generate transaction number
        transaction_number = f'TXN{timezone.now().strftime("%Y%m%d")}{uuid.uuid4().hex[:6].upper()}'
        
        # Get and validate caisse balance FIRST
        caisse = Caisse.objects.select_for_update().get(id=caisse_id)
        
        # CRITICAL FIX: Check if currency matches caisse currency
        if caisse.currency != currency_orig:
            raise ValidationError(f"Currency mismatch. Caisse {caisse.name} uses {caisse.currency.code}, but you selected {currency_orig.code}")
        
        # Calcul du montant requis théorique (informationnel)
        required_amount = amount_orig
        if op_type == 'WITHDRAWAL':
            # For withdrawal, we need the amount + fee
            required_amount = amount_orig + (fee / exchange_rate)
        
        # Le blocage a été retiré. Les agents peuvent toujours opérer.
        # if caisse.balance < required_amount:
        #     raise ValidationError(f"Fonds insuffisants...")
        
        # Create operation with PENDING status first
        operation = Operation.objects.create(
            transaction_number=transaction_number,
            agent=agent,
            caisse_id=caisse_id,
            type=op_type,
            amount_orig=amount_orig,
            currency_orig=currency_orig,
            amount_ref=amount_ref,
            currency_ref=currency_ref,
            exchange_rate=exchange_rate,
            fee_calculated=fee,
            observation=observation,
            status='PENDING'  # Start with PENDING status
        )
        
        # Update caisse balance
        if op_type == 'WITHDRAWAL':
            # Retrait: l'argent sort de la caisse (agent donne de l'argent au client)
            caisse.balance -= required_amount
        elif op_type == 'TRANSFER':
            # Transfert: l'agent reçoit l'argent du client + les frais
            caisse.balance += (amount_orig + fee)
        caisse.save()
        
        # Mark operation as completed
        operation.status = 'COMPLETED'
        operation.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=agent,
            action=AuditLog.ActionType.TRANSACTION,
            model_name='Operation',
            object_id=str(operation.id),
            object_repr=f"Operation {transaction_number}: {amount_orig} {currency_orig.code}",
            changes={
                'type': [None, op_type],
                'amount_orig': [None, str(amount_orig)],
                'currency_orig': [None, currency_orig.code],
                'caisse': [None, caisse.name]
            }
        )
        
        return operation
        
        # Log the operation
        AuditLog.log_action(
            user=agent,
            action=AuditLog.ActionType.TRANSACTION,
            model_name='operation',
            object_id=str(operation.pk),
            object_repr=f"Transaction {operation.transaction_number}",
            changes={
                'transaction_number': [None, operation.transaction_number],
                'amount_orig': [None, str(operation.amount_orig)],
                'amount_ref': [None, str(operation.amount_ref)],
                'fee_calculated': [None, str(operation.fee_calculated)],
                'type': [None, operation.type],
                'caisse_balance_before': [str(caisse.balance + amount_orig), str(caisse.balance)]
            }
        )
        
        return operation
    
    @staticmethod
    def _calculate_fee(amount, currency):
        """
        Calculate automatic fee based on fee grid in USD.
        
        LOGIQUE MÉTIER:
        - Une seule grille de frais existe en USD (devise de référence)
        - Si le montant est dans une autre devise (ex: EUR), il est d'abord converti en USD
        - On cherche alors la tranche correspondante dans la grille USD
        - Le frais retourné est toujours en USD
        
        Args:
            amount: Transaction amount (in any currency)
            currency: Currency object of the amount
            
        Returns:
            Decimal: Calculated fee in USD
        """
        from decimal import Decimal
        
        amount = Decimal(str(amount))
        
        # Get reference currency (USD)
        try:
            usd_currency = Currency.objects.get(code='USD')
        except Currency.DoesNotExist:
            raise ValidationError("USD currency not found. Please configure USD as reference currency.")
        
        # Convert amount to USD if necessary
        amount_in_usd = amount
        if currency.code != 'USD':
            try:
                from core.models import ExchangeRate
                # Chercher le taux de conversion vers USD
                rate_obj = ExchangeRate.objects.filter(
                    base_currency=currency,
                    target_currency=usd_currency
                ).first()
                
                if rate_obj:
                    amount_in_usd = amount * rate_obj.rate
                else:
                    # Essayer l'inverse (USD vers currency) et inverser le taux
                    inverse_rate_obj = ExchangeRate.objects.filter(
                        base_currency=usd_currency,
                        target_currency=currency
                    ).first()
                    if inverse_rate_obj:
                        amount_in_usd = amount / inverse_rate_obj.rate
                    else:
                        raise ValidationError(f"Aucun taux de change trouvé pour {currency.code} vers USD")
            except Exception as e:
                raise ValidationError(f"Erreur de conversion vers USD: {str(e)}")
        
        # Find matching fee grid in USD
        fee_grid = FeeGrid.objects.filter(
            currency=usd_currency,
            min_amount__lte=amount_in_usd,
            max_amount__gte=amount_in_usd
        ).first()
        
        if fee_grid:
            return fee_grid.fee_amount
        
        # Amount above max grid - return 0 (custom fee required)
        return Decimal('0')


def calculate_automatic_fee(amount, currency):
    """
    Calculate automatic fee based on the fee grid in USD.
    
    LOGIQUE MÉTIER:
    - Une seule grille de frais existe en USD (devise de référence)
    - Si le montant est dans une autre devise, il est d'abord converti en USD
    - On cherche la tranche dans la grille USD
    - Le frais retourné est toujours en USD
    
    Fee Grid (USD uniquement):
    - 0.10 $ – 40.00 $ → 5 $
    - 40.10 $ – 100.00 $ → 8 $
    - 100.10 $ – 200.00 $ → 15 $
    - 200.10 $ – 300.00 $ → 20 $
    - 300.10 $ – 400.00 $ → 26 $
    - 400.10 $ – 600.00 $ → 30 $
    - 600.10 $ – 800.00 $ → 35 $
    - 800.10 $ – 1 000.00 $ → 40 $
    - 1 000.10 $ – 1 500.00 $ → 45 $
    - 1 500.10 $ – 1 800.00 $ → 64 $
    - 1 800.10 $ – 2 000.00 $ → 80 $
    - Above 2000 $: Custom (admin defined)
    
    Args:
        amount: Transaction amount (in any currency)
        currency: Currency object
        
    Returns:
        tuple: (fee_amount in USD, fee_grid_entry or None for custom)
    """
    # Utiliser la même logique que _calculate_fee
    try:
        fee = OperationService._calculate_fee(amount, currency)
        
        # Retourner le frais et essayer de trouver la grille correspondante
        if fee > 0:
            usd_currency = Currency.objects.get(code='USD')
            
            # Convertir le montant en USD pour trouver la grille
            amount_usd = Decimal(str(amount))
            if currency.code != 'USD':
                from core.models import ExchangeRate
                rate_obj = ExchangeRate.objects.filter(
                    base_currency=currency,
                    target_currency=usd_currency
                ).first()
                if rate_obj:
                    amount_usd = amount_usd * rate_obj.rate
            
            fee_grid = FeeGrid.objects.filter(
                currency=usd_currency,
                min_amount__lte=amount_usd,
                max_amount__gte=amount_usd
            ).first()
            
            return fee, fee_grid
        else:
            return Decimal('0'), None
            
    except Exception as e:
        print(f"Error calculating fee: {e}")
        return Decimal('0'), None


def get_available_currencies():
    """Get all available currencies for operations"""
    return Currency.objects.all()


def get_operation_summary(operations):
    """
    Calculate summary statistics for operations.
    According to section 20 of specification.
    
    Returns:
        dict: Summary with volume, fees, counts
    """
    total_volume = operations.aggregate(Sum('amount_ref'))['amount_ref__sum'] or Decimal('0')
    total_fees = operations.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or Decimal('0')
    count = operations.count()
    
    transfers = operations.filter(type='TRANSFER').count()
    withdrawals = operations.filter(type='WITHDRAWAL').count()
    
    return {
        'total_volume': total_volume,
        'total_fees': total_fees,
        'count': count,
        'transfers': transfers,
        'withdrawals': withdrawals
    }


def calculate_financial_summary(start_date=None, end_date=None, agent=None):
    """
    Calculate complete financial summary.
    According to section 20 of specification.
    
    Formula: Bénéfice = frais collectés - dépenses - commissions agents
    
    Args:
        start_date: Start date filter
        end_date: End date filter
        agent: Filter by specific agent
        
    Returns:
        dict: Complete financial summary
    """
    from django.db.models import Q
    from django.utils import timezone
    from datetime import timedelta
    
    # Default to today if no dates specified
    if not end_date:
        end_date = timezone.now().date()
    if not start_date:
        start_date = end_date
    
    # Build filter
    date_filter = Q(date_time__date__gte=start_date) & Q(date_time__date__lte=end_date)
    if agent:
        date_filter &= Q(agent=agent)
    
    operations = Operation.objects.filter(date_filter)
    
    # Get financial data
    total_volume = operations.aggregate(Sum('amount_ref'))['amount_ref__sum'] or Decimal('0')
    total_fees = operations.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or Decimal('0')
    
    # Calculate agent commissions
    total_commissions = Decimal('0')
    for op in operations:
        if op.agent.commission_rate:
            commission = (op.fee_calculated * op.agent.commission_rate) / Decimal('100')
            total_commissions += commission
    
    # Get expenses
    expense_filter = Q(date__gte=start_date) & Q(date__lte=end_date)
    expenses = Expense.objects.filter(expense_filter)
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # Calculate net profit
    net_profit = total_fees - total_expenses - total_commissions
    
    return {
        'period': {
            'start': start_date,
            'end': end_date
        },
        'operations': {
            'volume': total_volume,
            'fees': total_fees,
            'count': operations.count()
        },
        'expenses': total_expenses,
        'commissions': total_commissions,
        'net_profit': net_profit
    }


def get_agent_performance(agent, start_date=None, end_date=None):
    """
    Calculate agent performance metrics.
    According to section 14 of specification.
    
    Args:
        agent: Agent user object
        start_date: Start date
        end_date: End date
        
    Returns:
        dict: Agent performance data
    """
    from django.db.models import Q
    from django.utils import timezone
    
    if not end_date:
        end_date = timezone.now().date()
    if not start_date:
        start_date = end_date
    
    operations = Operation.objects.filter(
        agent=agent,
        date_time__date__gte=start_date,
        date_time__date__lte=end_date
    )
    
    total_fees = operations.aggregate(Sum('fee_calculated'))['fee_calculated__sum'] or Decimal('0')
    count = operations.count()
    
    # Calculate commission
    commission_rate = agent.commission_rate or Decimal('0')
    commission_amount = (total_fees * commission_rate) / Decimal('100')
    
    return {
        'agent': agent,
        'period': {'start': start_date, 'end': end_date},
        'total_operations': count,
        'total_fees_generated': total_fees,
        'commission_rate': commission_rate,
        'commission_amount': commission_amount
    }


def get_caisse_balance(caisse):
    """
    Get current balance of a caisse.
    According to section 12 of specification.
    
    Args:
        caisse: Caisse object
        
    Returns:
        dict: Caisse balance information
    """
    return {
        'caisse': caisse,
        'balance': caisse.balance,
        'currency': caisse.currency,
        'agent': caisse.agent,
        'name': caisse.name
    }
