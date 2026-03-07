# django-meeting

Application web de planification de réunions (type Doodle) avec vote sur créneaux horaires.

## Description

**django-meeting** permet à des organisateurs authentifiés de créer des sondages de disponibilité et d'inviter des participants (par email) à voter sur des créneaux horaires. Les participants accèdent au sondage via un lien unique personnel, sans compte requis.

### Fonctionnalités

- Création de sondages avec créneaux horaires via un calendrier interactif (FullCalendar)
- Invitation des participants par email avec lien de vote unique
- Vote par créneau : Oui ✓, Peut-être ?, Non ✗
- Récapitulatif créateur avec tableau de votes, scores pondérés et meilleur créneau mis en évidence
- Résumé anonymisé des votes côté participant
- Clôture manuelle ou automatique (deadline)
- Choix du créneau final avec notification email à tous les participants
- Relance des non-répondants
- Charte graphique (couleurs, logo) configurable via l'admin
- Responsive mobile

---

## Prérequis

### Développement local

- Python 3.12+
- pip

### Production (Docker)

- Docker
- Docker Compose

---

## Installation en développement

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd django-meeting

# Créer et activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou : .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur (accès à l'admin)
python manage.py createsuperuser

# Lancer le serveur de développement
python manage.py runserver
```

L'application est accessible à `http://localhost:8000`.
L'interface d'administration est accessible à `http://localhost:8000/admin/`.

> Aucune variable d'environnement n'est requise en développement. Les emails sont affichés dans la console.

---

## Déploiement Docker

```bash
# Copier et adapter le fichier d'environnement
cp .env.example .env
nano .env  # Renseigner SECRET_KEY, ALLOWED_HOSTS, etc.

# Construire et démarrer
docker compose up -d

# Créer le superutilisateur (première fois)
docker compose exec web python manage.py createsuperuser
```

L'application est accessible à `http://localhost:8768`.

### Volumes

| Volume local | Contenu |
|---|---|
| `./db_data/` | Base de données SQLite (montée dans `/data/`) |
| `./media_data/` | Fichiers uploadés, logo (montés dans `/app/media/`) |

Ces dossiers sont créés automatiquement par Docker et ignorés par git.

---

## Configuration admin

Connectez-vous à `/admin/` avec le superutilisateur pour :

### 1. Configuration du site (`Site Configuration`)

| Paramètre | Description |
|---|---|
| Nom du site | Affiché dans l'interface et les emails |
| Logo | Image PNG/JPG affichée dans le header |
| Couleur primaire | Couleur hex (ex: `#2563eb`) |
| Couleur secondaire | Couleur hex (ex: `#1e40af`) |
| Serveur SMTP | Adresse du serveur SMTP (ex: `smtp.gmail.com`) |
| Port SMTP | Port (défaut: 587) |
| TLS activé | Activer/désactiver TLS |
| Identifiant SMTP | Nom d'utilisateur SMTP |
| Mot de passe SMTP | Mot de passe SMTP |
| Email expéditeur | Adresse d'expédition des emails |
| Rétention (jours) | Délai avant suppression automatique après clôture (défaut: 90) |

> Si aucun SMTP n'est configuré, les emails sont affichés dans la console en développement.

### 2. Créer des comptes créateurs

Dans `Utilisateurs`, créez des utilisateurs standard (sans `is_staff` ni `is_superuser`). Ces utilisateurs pourront se connecter sur `/login/` et créer des sondages.

---

## Variables d'environnement

| Variable | Description | Défaut (dev) |
|---|---|---|
| `SECRET_KEY` | Clé secrète Django | Valeur de dev |
| `DEBUG` | Mode debug | `True` |
| `ALLOWED_HOSTS` | Hôtes autorisés (virgule) | `*` si DEBUG=True |
| `DATABASE_PATH` | Chemin fichier SQLite | `db.sqlite3` dans le projet |

---

## Architecture

```
django-meeting/
├── config/           # Configuration Django (settings, urls, wsgi)
├── apps/
│   ├── site_config/  # Singleton de configuration du site
│   ├── accounts/     # Authentification créateurs
│   └── polls/        # App principale
│       ├── models.py # Poll, TimeSlot, Participant, Vote
│       ├── views.py  # Vues créateur + participant + API
│       ├── email.py  # Envoi email dynamique via SiteConfiguration
│       ├── tasks.py  # Tâches planifiées (apscheduler)
│       └── tokens.py # Génération de tokens
├── templates/        # Templates Django (base.html, polls/, accounts/, emails/)
└── static/           # CSS + JS (calendar_create.js, calendar_vote.js)
```

### Stack technique

| Composant | Technologie |
|---|---|
| Backend | Django 5.x |
| Serveur WSGI | Gunicorn |
| Fichiers statiques | WhiteNoise |
| Base de données | SQLite |
| Tâches planifiées | django-apscheduler |
| Calendrier | FullCalendar 6 (CDN) |
| Conteneurisation | Docker + Docker Compose |

---

## URLs

| URL | Description |
|---|---|
| `/` | Liste des sondages (créateur connecté) |
| `/login/` | Connexion |
| `/poll/create/` | Créer un sondage |
| `/poll/<uuid>/` | Détail / récapitulatif (créateur) |
| `/poll/<uuid>/edit/` | Modifier un sondage |
| `/poll/<uuid>/vote/<token>/` | Interface de vote (participant) |
| `/api/poll/<uuid>/summary/` | API JSON des compteurs anonymisés |
| `/admin/` | Administration Django |
