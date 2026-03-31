#!/bin/bash
set -e

echo "Starting Rapid Cash deployment..."

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if needed (optional - only for first deploy)
# python manage.py createsuperuser --noinput || true

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
