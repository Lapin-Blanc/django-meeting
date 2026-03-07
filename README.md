# django-meeting

Application web de planification de réunions (type Doodle) avec vote sur créneaux horaires.

## Description

django-meeting permet à des créateurs de proposer des créneaux horaires et à des participants de voter pour leurs disponibilités, sans nécessiter de compte utilisateur pour les participants (accès par lien unique).

## Prérequis

- Python 3.12+
- pip

## Installation en développement

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd django-meeting

# Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

L'application est accessible à `http://localhost:8000`.

L'interface d'administration est accessible à `http://localhost:8000/admin/`.

## Configuration (développement)

Aucune variable d'environnement n'est requise en développement. Les valeurs par défaut sont adaptées au développement local :

- `DEBUG=True`
- `SECRET_KEY` : clé par défaut (ne pas utiliser en production)
- Base de données SQLite dans `db.sqlite3`
- Emails affichés dans la console

## Déploiement Docker

```bash
# Copier et adapter le fichier d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# Construire et démarrer
docker compose up -d
```

L'application est accessible à `http://localhost:8768`.

## Variables d'environnement

Voir `.env.example` pour la liste complète des variables avec leur description.

| Variable | Description | Défaut (dev) |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | Valeur de dev |
| `DEBUG` | Mode debug | `True` |
| `ALLOWED_HOSTS` | Hôtes autorisés (virgule) | `*` si DEBUG |
| `DATABASE_PATH` | Chemin SQLite | `db.sqlite3` |

## Configuration admin

Après installation, connectez-vous à l'admin Django (`/admin/`) avec le superutilisateur pour :

1. **Configuration du site** : renseigner le nom du site, logo, couleurs, paramètres SMTP
2. **Créer des comptes créateurs** : créer des utilisateurs Django standard (sans `is_staff`)

## Structure du projet

```
django-meeting/
├── config/          # Paramètres Django (settings.py, urls.py, wsgi.py)
├── apps/
│   ├── site_config/ # Configuration singleton du site
│   ├── accounts/    # Authentification créateurs
│   └── polls/       # App principale (sondages, votes)
├── templates/       # Templates Django
├── static/          # CSS et JavaScript
└── media/           # Fichiers uploadés (logo)
```
