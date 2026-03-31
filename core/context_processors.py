import json
import sys
from django.db import OperationalError, ProgrammingError

def fee_grid_processor(request):
    """
    Context processor to inject the DB-driven FeeGrid into templates.
    Returns empty array if DB is not available (e.g., during collectstatic).
    """
    # Skip DB queries during collectstatic
    if 'collectstatic' in sys.argv:
        return {'fee_grid_json': '[]'}
    
    try:
        from operations.models import FeeGrid
        # We only need the reference currency grid (USD) for the UI calculations
        grids = FeeGrid.objects.filter(currency__code='USD').order_by('min_amount')
        
        # Force evaluation to catch DB errors early
        grid_list = list(grids.values('min_amount', 'max_amount', 'fee_amount'))
        
        # Convert to the expected format
        result = []
        for g in grid_list:
            result.append({
                'min': float(g['min_amount']),
                'max': float(g['max_amount']),
                'fee': float(g['fee_amount'])
            })
            
        return {'fee_grid_json': json.dumps(result)}
        
    except (OperationalError, ProgrammingError):
        # DB not ready or table doesn't exist yet
        return {'fee_grid_json': '[]'}
    except Exception:
        # Any other error (including import errors), return empty
        return {'fee_grid_json': '[]'}
