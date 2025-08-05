#!/bin/sh

# Wait for DB
echo "Waiting for postgres..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL started"

# Migrate and collectstatic
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Run Gunicorn
exec gunicorn credit_system.wsgi:application --bind 0.0.0.0:8000