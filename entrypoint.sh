#!/bin/sh

echo "Running database migrations..."
/app/.venv/bin/python manage.py migrate

echo "Starting the server..."
/app/.venv/bin/python manage.py runserver 0.0.0.0:8000
