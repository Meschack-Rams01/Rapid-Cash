import json
from operations.models import FeeGrid

def fee_grid_processor(request):
    """
    Context processor to inject the DB-driven FeeGrid into templates.
    This allows the frontend JavaScript to stay in sync with the backend.
    """
    try:
        # We only need the reference currency grid (USD) for the UI calculations
        grids = FeeGrid.objects.filter(currency__code='USD').order_by('min_amount')
        
        grid_list = []
        for g in grids:
            grid_list.append({
                'min': float(g.min_amount),
                'max': float(g.max_amount),
                'fee': float(g.fee_amount)
            })
            
        return {'fee_grid_json': json.dumps(grid_list)}
    except Exception:
        # If DB is not ready or no grid exists, return empty array to fallback on JS
        return {'fee_grid_json': '[]'}
