#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py makemigrations accounts
python manage.py makemigrations courses
python manage.py migrate
python manage.py create_admin
