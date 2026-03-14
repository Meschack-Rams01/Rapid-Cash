import os
import re

core_url_names = [
    'capital_management', 'payroll_dashboard', 'calculate_salaries', 'pay_salary', 'add_bonus',
    'agents_list', 'create_agent', 'edit_agent', 'delete_user',
    'associates_list', 'create_associate', 'investors_list', 'create_investor',
    'caisses_list', 'exchange_rates', 'user_profile'
]

template_dir = 'c:/Users/User/Desktop/rapid cash/rapid_cash_project/templates'
view_dir = 'c:/Users/User/Desktop/rapid cash/rapid_cash_project'

files_modified = 0

# Fix templates
for root, _, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for name in core_url_names:
                # regex to match {% url 'name' ... %} or {% url "name" ... %} without core:
                pattern = r"\{%\s*url\s+['\"](" + name + r")['\"]"
                content = re.sub(pattern, r"{% url 'core:\1'", content)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_modified += 1
                print(f"Fixed template {filepath}")

# Fix views
for root, _, files in os.walk(view_dir):
    if 'venv' in root or '.git' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('views.py') or file.endswith('views_auth.py') or file == 'tests_services.py':
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for name in core_url_names:
                # match redirect('name') or reverse('name')
                pattern_redirect = r"redirect\(['\"]" + name + r"['\"]\)"
                content = re.sub(pattern_redirect, f"redirect('core:{name}')", content)

                pattern_reverse = r"reverse\(['\"]" + name + r"['\"]\)"
                content = re.sub(pattern_reverse, f"reverse('core:{name}')", content)
                
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_modified += 1
                print(f"Fixed view {filepath}")

print(f"Total files modified: {files_modified}")
