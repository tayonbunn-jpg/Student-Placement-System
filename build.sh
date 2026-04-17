#!/usr/bin/env bash
# Exit on error
set -o errexit

# Print commands for debugging
set -o xtrace

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Create superuser if it doesn't exist (optional - you can comment this out)
# python manage.py createsuperuser --no-input --username admin --email admin@example.com || true

echo "✅ Build completed successfully!"