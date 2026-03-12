# Rapid-Cash

Système de gestion des opérations de change et transferts d'argent.

## Fonctionnalités

- Gestion des opérations (Transferts, Retraits)
- Gestion multi-devises avec conversion automatique
- Grille de frais automatique
- Gestion des agents et commissions
- Tableau de bord avec statistiques
- Gestion de la paie
- Rapports et exports PDF

## Dépendances

- Django 5.x
- Python 3.11+
- Tailwind CSS

## Installation

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Devises supportées

- USD (Référence)
- EUR
- CDF
- GBP
- TRY
