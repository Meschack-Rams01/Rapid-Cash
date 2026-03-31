# Déploiement sur Render.com - Guide Rapide

## Prérequis

1. **Créer un compte Render** : https://render.com
2. **Connecter votre repo GitHub/GitLab** à Render

## Étapes de Déploiement

### 1. Créer un Blueprint sur Render

1. Allez sur https://dashboard.render.com/blueprints
2. Cliquez sur **"New Blueprint Instance"**
3. Connectez votre repository GitHub/GitLab contenant le projet
4. Render détectera automatiquement le fichier `render.yaml`

### 2. Configuration Automatique

Le fichier `render.yaml` crée automatiquement :
- ✅ **Web Service** : Application Django (gunicorn)
- ✅ **Worker** : Celery pour les tâches asynchrones
- ✅ **PostgreSQL** : Base de données
- ✅ **Redis** : Cache et broker Celery

### 3. Variables d'Environnement (Auto-générées)

| Variable | Source | Description |
|----------|--------|-------------|
| `SECRET_KEY` | Auto-générée | Clé secrète Django |
| `DATABASE_URL` | Base PostgreSQL | Connexion DB |
| `REDIS_URL` | Service Redis | Connexion Redis |
| `DJANGO_SETTINGS_MODULE` | Définie | `config.production` |

### 4. Déploiement

Une fois le Blueprint créé, Render déploie automatiquement :
1. Build des dépendances (`pip install`)
2. Collecte des fichiers statiques
3. Migrations de base de données
4. Démarrage des services (Web + Celery Worker)

### 5. Créer un Superutilisateur

Dans le dashboard Render :
1. Allez dans votre **Web Service**
2. Cliquez sur **"Shell"** dans le menu
3. Exécutez :
   ```bash
   python manage.py createsuperuser
   ```

## Commandes Utiles

| Action | Commande/Emplacement |
|--------|---------------------|
| Voir les logs | Dashboard → Web Service → Logs |
| Redeployer | Dashboard → Manual Deploy → Deploy Latest Commit |
| Shell access | Dashboard → Web Service → Shell |
| Variables env | Dashboard → Web Service → Environment |

## URL de l'Application

Après déploiement, votre application sera accessible à :
```
https://rapid-cash.onrender.com
```

## Coûts (Plan Starter - Gratuit)

- **Web Service** : Gratuit (spin down after 15 min inactivity)
- **Worker** : Gratuit
- **PostgreSQL** : Gratuit (1 GB)
- **Redis** : Gratuit (25 MB)

**Note** : Le plan gratuit a des limitations :
- Le web service "s'endort" après 15 min d'inactivité
- Le worker redémarre régulièrement
- Pour production, considérez le plan Starter ($7/mois/service)

## Dépannage

### Problème : Static files 404
Vérifier dans le dashboard que `collectstatic` s'est bien exécuté dans les logs de build.

### Problème : Database connection failed
Vérifier que `DATABASE_URL` est bien définie dans les variables d'environnement.

### Problème : Celery ne fonctionne pas
Vérifier que `REDIS_URL` est bien définie et que le service Redis est actif.

### Rebuild manuel
Dans le dashboard : **Manual Deploy → Deploy Latest Commit**

## Fichiers de Configuration

```
rapid_cash_project/
├── render.yaml          # Configuration Blueprint Render
├── build.sh             # Script de build
├── config/
│   └── production.py    # Settings production (compatible Render/Fly.io)
└── RENDER-DEPLOY.md     # Ce guide
```

## Différences Fly.io vs Render

| Aspect | Fly.io | Render |
|--------|--------|--------|
| Docker | Oui (Dockerfile) | Non (natif Python) |
| CLI | `flyctl` | Dashboard web |
| Pricing | Usage-based | Service-based |
| Cold Start | Non | Oui (plan gratuit) |
| Redis/Postgres | Intégré | Intégré |
| Custom Domain | Oui | Oui |

**Render est plus simple** pour démarrer (pas de Dockerfile nécessaire).
