#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Standalone test script to verify all pages work correctly"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from core.models import User

# Create test client
client = Client()

# Get admin user
user = User.objects.filter(role='ADMIN').first()
if not user:
    print("ERROR: No admin user found!")
    sys.exit(1)

# Force login
client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

print(f"Testing with user: {user.username} (role: {user.role})")
print("=" * 50)

# Test all pages
pages = [
    ('/', 'Home'),
    ('/dashboard/', 'Dashboard'),
    ('/operations/nouveau/', 'Create Operation'),
    ('/operations/liste/', 'Operation List'),
    ('/core/agents/', 'Agents List'),
    ('/core/caisses/', 'Caisses List'),
    ('/finance/depenses/', 'Expense List'),
    ('/finance/depenses/ajouter/', 'Create Expense'),
]

errors = []
success_count = 0

for url, name in pages:
    try:
        response = client.get(url)
        status = response.status_code
        if status == 200:
            print(f"[OK] {name}: {url} - Status: {status}")
            success_count += 1
        else:
            print(f"[FAIL] {name}: {url} - Status: {status}")
            errors.append(f"{name}: {url} - {status}")
    except Exception as e:
        print(f"[FAIL] {name}: {url} - ERROR: {str(e)}")
        errors.append(f"{name}: {url} - {str(e)}")

print("=" * 50)
print(f"Tested: {len(pages)} pages, Success: {success_count}, Failed: {len(errors)}")

if errors:
    print("\nERRORS FOUND:")
    for err in errors:
        print(f"  - {err}")
    # Don't use sys.exit in test scripts - let Django handle the exit code
    raise SystemExit(1)
else:
    print("ALL PAGES WORKING CORRECTLY!")
