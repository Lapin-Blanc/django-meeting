# CLAUDE.md — Instructions pour Claude Code

## Projet

**django-meeting** : application web Django de planification de réunions (type Doodle) avec vote sur créneaux horaires.

## Documentation

Lire impérativement `docs/SPEC.md` avant toute implémentation. Ce fichier contient la spécification complète : modèle de données, fonctionnalités, URLs, architecture, sécurité.

## Principes fondamentaux

### Stack stricte

- **Backend** : Django 5.x, server-side rendering avec Django Templates
- **Frontend** : CSS custom + vanilla JavaScript. **INTERDIT** : React, Vue, Angular, Tailwind, HTMX, Alpine.js ou tout autre framework/lib JS (sauf FullCalendar)
- **Calendrier** : FullCalendar via CDN (pas d'installation npm)
- **Base de données** : SQLite
- **Serveur** : Gunicorn + WhiteNoise
- **Tâches planifiées** : django-apscheduler

### Conventions

- Langue du code : anglais (noms de variables, fonctions, classes, commentaires)
- Langue de l'interface : français (templates, messages, labels de formulaire, emails)
- UUIDs comme clés primaires sur tous les modèles métier
- Respecter la structure de dossiers définie dans SPEC.md (apps/ contient les apps Django)
- Un fichier `apps/__init__.py` vide, chaque app dans son sous-dossier
- Settings dans `config/settings.py`, URLs racine dans `config/urls.py`

### Qualité

- Chaque vue métier doit vérifier les permissions (créateur = propriétaire, participant = token valide)
- Pas de logique métier dans les templates — garder les vues et les modèles responsables
- Les formulaires utilisent les classes `forms.ModelForm` ou `forms.Form` Django
- Les messages utilisateur utilisent le framework `django.contrib.messages`
- Tester les cas limites : sondage clôturé, token invalide, deadline dépassée, créneau supprimé

## Scoring des créneaux

Pondération des votes : `yes` = 1.0, `maybe` = 0.5, `no` = 0.0. Le score d'un créneau est la somme des poids. Implémenter en tant que propriété/méthode sur `TimeSlot` ou via annotation QuerySet. Ce score est affiché dans le récapitulatif créateur (en-tête de colonnes, tri décroissant, meilleur créneau mis en évidence) et dans le résumé anonymisé participant.

## Configuration email dynamique

Point critique : l'envoi d'email ne doit PAS utiliser les settings Django (`EMAIL_HOST`, etc.). Implémenter un backend ou une fonction utilitaire dans `apps/polls/email.py` qui :
1. Lit les paramètres SMTP depuis `SiteConfiguration` à chaque envoi
2. Crée une connexion SMTP à la volée
3. Gère les erreurs de connexion SMTP gracieusement (log + message utilisateur)

## Calendrier FullCalendar

Composant central et le plus complexe. Deux fichiers JS distincts :

### `static/js/calendar_create.js`
- Initialise FullCalendar en mode interactif (selectable, editable, eventResizeable)
- Click-drag pour créer un créneau → ajoute un événement gris
- Événements déplaçables et redimensionnables
- Bouton/icône de suppression sur chaque événement
- Stocke les créneaux dans un tableau JS, sérialisé en JSON dans un champ hidden du formulaire avant soumission
- Vues : timeGridWeek (défaut) + dayGridMonth, avec boutons de bascule

### `static/js/calendar_vote.js`
- Initialise FullCalendar en mode lecture (non editable, non selectable)
- Affiche les créneaux du sondage comme événements
- Chaque événement contient 3 icônes cliquables (✓ ? ✗) rendues via `eventContent`
- Au clic sur une icône : change la couleur de l'événement (vert/orange/rouge) et stocke le choix
- Gris = pas encore voté
- Bouton « Enregistrer » envoie les choix en POST (JSON ou formulaire)
- Si sondage clôturé : pas d'icônes, couleurs selon vote enregistré, créneau retenu mis en évidence
- Vues : timeGridWeek (défaut) + dayGridMonth

### Responsive
- Sur écran < 768px : basculer automatiquement en `listWeek` ou `timeGridDay`
- Zones de tap minimum 44×44px pour les icônes de vote

## Docker

- `Dockerfile` : python:3.12-slim, pip install, collectstatic au build, gunicorn sur port **8768** en entrypoint
- `docker-compose.yml` : un seul service `web`, port `8768:8768`, **bind mounts relatifs** (`./db_data:/data` et `./media_data:/app/media`), env_file `.env`
- Fournir un `.env.example` documenté
- Le `entrypoint` ou un script de démarrage doit exécuter `migrate` avant de lancer gunicorn
- Les dossiers `db_data/` et `media_data/` doivent être dans le `.gitignore`

## Mode développement

Le projet DOIT être testable sans Docker via `python manage.py runserver` :
- `settings.py` fonctionne sans aucune variable d'environnement (valeurs par défaut sensées pour le dev)
- `DEBUG=True` par défaut, `SECRET_KEY` par défaut en dev, `ALLOWED_HOSTS=["*"]` en debug
- SQLite dans `BASE_DIR / "db.sqlite3"` par défaut (le chemin `/data/db.sqlite3` est surchargé via env en Docker)
- Si SMTP non configuré dans `SiteConfiguration` → fallback sur `console.EmailBackend`
- `db.sqlite3` dans le `.gitignore`

## Tâches planifiées

Utiliser `django-apscheduler` avec enregistrement des jobs au démarrage (dans `apps/polls/apps.py` → `ready()` ou via un module dédié).

Deux jobs :
1. `close_expired_polls` : toutes les 5 minutes
2. `purge_old_polls` : une fois par jour à 3h00

## Fichiers racine à produire

- `README.md` : documentation complète (description, prérequis, installation en dev, déploiement Docker, configuration admin, variables d'environnement)
- `.gitignore` : adapté Python/Django (venv, __pycache__, db.sqlite3, .env, db_data/, media_data/, staticfiles/, *.pyc, media/)
- `.env.example` : toutes les variables avec valeurs d'exemple commentées
- `requirements.txt` : dépendances Python épinglées

## Ordre d'implémentation suggéré

1. Setup projet Django + structure dossiers + `.gitignore` + config Docker
2. App `site_config` : modèle singleton + admin + context processor
3. App `accounts` : login/logout/password reset
4. App `polls` — modèles : Poll, TimeSlot, Participant, Vote (+ scoring §2.6)
5. App `polls` — vues créateur : liste, création (formulaire + calendrier), détail/récap, modification, suppression
6. App `polls` — logique email : backend dynamique + templates email
7. App `polls` — vues participant : vote (calendrier + soumission), lecture seule
8. App `polls` — API summary (JSON, compteurs anonymisés + score)
9. App `polls` — actions créateur : clôture, choix final, relance
10. Tâches planifiées (apscheduler)
11. CSS + responsive + charte graphique dynamique
12. Docker final + `.env.example` + `README.md`
