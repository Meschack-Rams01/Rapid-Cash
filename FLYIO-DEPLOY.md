# Déploiement sur Fly.io - Guide Rapide

## Prérequis

1. **Créer un compte Fly.io**: https://fly.io/
2. **Installer Fly CLI**:
   ```powershell
   # Windows (PowerShell)
   winget install FlyIO.flyctl
   # ou
   iwr https://fly.io/install.ps1 -useb | iex
   ```

3. **Se connecter**:
   ```bash
   fly auth login
   ```

## Étapes de Déploiement

### 1. Lancer l'application Fly.io

```bash
cd "c:\Users\User\Desktop\rapid cash\rapid_cash_project"
fly launch
```

**Réponses suggérées**:
- App name: `rapid-cash-app` (ou laissez Fly en générer un)
- Region: `cdg` (Paris) - plus proche de Kinshasa
- Would you like to set up a Postgresql database now?: **Yes**
- Select configuration: **Development** (pour commencer)
- Would you like to set up an Upstash Redis database now?: **Yes** (nécessaire pour Celery)

### 2. Configurer les Secrets (Variables d'Environnement)

```bash
fly secrets set DJANGO_SETTINGS_MODULE=config.production
fly secrets set SECRET_KEY="votre-cle-super-secrete-ici-min-50-caracteres"
fly secrets set DEBUG=False
fly secrets set ALLOWED_HOSTS="votre-app.fly.dev,localhost"
```

**Générer une clé secrète Django**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Déployer

```bash
fly deploy
```

### 4. Créer un Superutilisateur

```bash
fly ssh console -C "python manage.py createsuperuser"
```

### 5. Voir les Logs

```bash
fly logs
```

### 6. Ouvrir l'Application

```bash
fly open
```

## Commandes Utiles

| Commande | Description |
|----------|-------------|
| `fly status` | Voir le statut de l'app |
| `fly logs` | Voir les logs en temps réel |
| `fly ssh console` | Accès SSH au conteneur |
| `fly apps list` | Lister les applications |
| `fly volumes list` | Lister les volumes |
| `fly postgres list` | Lister les bases Postgres |

## Structure des Fichiers Créés

```
rapid_cash_project/
├── Dockerfile          # Configuration Docker
├── fly.toml            # Configuration Fly.io (sera généré par fly launch)
├── start.sh            # Script de démarrage
├── .dockerignore       # Fichiers ignorés par Docker
└── config/
    └── production.py   # Settings production (modifié)
```

## Coûts

- **Plan Gratuit**: Jusqu'à 3 machines partagées, 1GB stockage, base Postgres 256MB
- **Postgres**: ~$2-5/mois pour une base de développement
- **Redis**: ~$2-5/mois pour le plan de base

## Dépannage

### Problème: Build échoue
```bash
fly deploy --no-cache
```

### Problème: Base de données non connectée
```bash
fly postgres attach --app rapid-cash-app
```

### Problème: Static files 404
Vérifier que `collectstatic` fonctionne dans le Dockerfile.

### Problème: Redis non connecté
```bash
fly redis list
fly redis status <nom-redis>
```

## Notes Importantes

1. **Base de données**: Fly.io crée automatiquement une base Postgres. L'URL est automatiquement injectée via `DATABASE_URL`.

2. **Redis**: Nécessaire pour Celery (tâches asynchrones). L'URL est automatiquement injectée via `REDIS_URL`.

3. **Static Files**: Servis automatiquement par Whitenoise (configuré dans `production.py`).

4. **Media Files**: Stockés sur le volume persistant `/app/data/media/`. Configurer dans `settings.py` si nécessaire.

5. **Migrations**: Exécutées automatiquement au démarrage via `start.sh`.
