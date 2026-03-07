# django-meeting — Spécification fonctionnelle et technique

## 1. Vue d'ensemble

**django-meeting** est une application web de planification de réunions, de type Doodle, permettant à des créateurs de proposer des créneaux horaires et à des participants de voter pour leurs disponibilités.

### 1.1 Principes directeurs

- Application Django server-side rendering (templates Django, CSS custom, vanilla JS)
- Aucun framework JS frontend (pas de React, Vue, Angular, ni Tailwind)
- Interface intégralement en français
- Déploiement via Docker Compose
- Simplicité et maintenabilité

### 1.2 Acteurs

| Acteur | Description |
|---|---|
| **Superutilisateur** | Administrateur Django, crée les comptes créateurs via l'admin |
| **Créateur** | Utilisateur Django authentifié, crée et gère des sondages |
| **Participant** | Personne invitée par email, accède au sondage via un lien unique (token), sans compte |

---

## 2. Modèle de données

### 2.1 SiteConfiguration (singleton)

Modèle singleton accessible uniquement via l'admin Django.

| Champ | Type | Description |
|---|---|---|
| `site_name` | CharField(100) | Nom affiché dans l'interface et les emails |
| `logo` | ImageField (optionnel) | Logo du site |
| `primary_color` | CharField(7) | Couleur primaire hex (ex: `#2563eb`) |
| `secondary_color` | CharField(7) | Couleur secondaire hex |
| `smtp_host` | CharField(255) | Serveur SMTP |
| `smtp_port` | PositiveIntegerField | Port SMTP (défaut: 587) |
| `smtp_use_tls` | BooleanField | TLS activé (défaut: True) |
| `smtp_username` | CharField(255) | Identifiant SMTP |
| `smtp_password` | CharField(255) | Mot de passe SMTP (stocké chiffré) |
| `smtp_from_email` | EmailField | Adresse d'expédition |
| `retention_days` | PositiveIntegerField | Nombre de jours avant suppression auto après clôture (défaut: 90) |

**Contrainte** : une seule instance en base (pattern singleton Django, ex: via `django-solo` ou implémentation manuelle).

L'envoi d'email dans toute l'application doit utiliser dynamiquement les paramètres SMTP de ce modèle (pas les settings Django statiques).

### 2.2 Poll (sondage)

| Champ | Type | Description |
|---|---|---|
| `id` | UUIDField (pk) | Identifiant unique |
| `creator` | ForeignKey(User) | Créateur du sondage |
| `title` | CharField(200) | Titre du sondage |
| `description` | TextField (optionnel) | Description / contexte |
| `location` | CharField(200, optionnel) | Lieu de la réunion |
| `deadline` | DateTimeField | Date limite de vote (clôture automatique) |
| `is_closed` | BooleanField | Clôture manuelle (défaut: False) |
| `chosen_slot` | ForeignKey(TimeSlot, null) | Créneau retenu par le créateur |
| `created_at` | DateTimeField(auto_now_add) | Date de création |
| `closed_at` | DateTimeField(null) | Date effective de clôture |

**Propriété calculée** : `is_active` → `not is_closed and deadline > now()`

### 2.3 TimeSlot (créneau horaire)

| Champ | Type | Description |
|---|---|---|
| `id` | UUIDField (pk) | Identifiant unique |
| `poll` | ForeignKey(Poll, CASCADE) | Sondage parent |
| `start` | DateTimeField | Début du créneau |
| `end` | DateTimeField | Fin du créneau |

**Contraintes** :
- `end > start`
- Pas de chevauchement entre créneaux d'un même sondage
- Ordonnés par `start` par défaut

### 2.4 Participant

| Champ | Type | Description |
|---|---|---|
| `id` | UUIDField (pk) | Identifiant unique |
| `poll` | ForeignKey(Poll, CASCADE) | Sondage associé |
| `name` | CharField(100) | Nom affiché du participant |
| `email` | EmailField | Adresse email |
| `token` | CharField(64, unique) | Token d'accès unique (généré automatiquement, cryptographiquement sûr) |
| `has_voted` | BooleanField | A déjà soumis au moins une réponse (défaut: False) |
| `invited_at` | DateTimeField(auto_now_add) | Date d'invitation |
| `last_voted_at` | DateTimeField(null) | Dernière soumission de vote |

**Contrainte** : unicité sur `(poll, email)`

### 2.5 Vote

| Champ | Type | Description |
|---|---|---|
| `id` | UUIDField (pk) | Identifiant unique |
| `participant` | ForeignKey(Participant, CASCADE) | Participant |
| `time_slot` | ForeignKey(TimeSlot, CASCADE) | Créneau concerné |
| `choice` | CharField avec choix | `yes`, `maybe`, `no` |
| `updated_at` | DateTimeField(auto_now) | Dernière modification |

**Contrainte** : unicité sur `(participant, time_slot)`

### 2.6 Pondération des votes (scoring)

Chaque créneau d'un sondage possède un **score** calculé à partir des votes reçus, servant à identifier le(s) meilleur(s) créneau(x).

| Choix | Poids |
|---|---|
| `yes` | **1.0** |
| `maybe` | **0.5** |
| `no` | **0.0** |

**Score d'un créneau** = somme des poids des votes reçus pour ce créneau.

Exemples : un créneau avec 3 « Oui », 2 « Peut-être » et 1 « Non » obtient un score de 3×1.0 + 2×0.5 + 1×0.0 = **4.0**.

Ce score est utilisé :
- Dans la **vue récapitulatif du créateur** : les créneaux sont triés par score décroissant, le(s) meilleur(s) sont mis en évidence
- Dans le **résumé anonymisé** (côté participant) : le score est affiché à côté des compteurs pour chaque créneau
- Implémentation : méthode ou propriété sur le modèle `TimeSlot` (ex: `@property def score`) ou annotation QuerySet

---

## 3. Fonctionnalités détaillées

### 3.1 Gestion des créateurs

- Les comptes créateurs sont des `User` Django standards, créés par le superutilisateur via l'admin
- Ils n'ont **pas** le statut `is_staff` (pas d'accès à l'admin Django)
- Ils disposent des permissions : créer, modifier, supprimer **leurs propres** sondages uniquement
- Connexion via une page `/login/` dédiée (formulaire classique Django)
- Fonctionnalité de réinitialisation de mot de passe par email (`/password-reset/`)

### 3.2 Cycle de vie d'un sondage

#### 3.2.1 Création

1. Le créateur authentifié accède au formulaire de création
2. Il renseigne : titre, description (optionnel), lieu (optionnel), date limite de vote
3. Il définit les créneaux horaires via l'interface calendrier (voir §4)
4. Il saisit la liste des participants (nom + email), avec possibilité d'ajouter/retirer des lignes dynamiquement
5. À la validation, le système :
   - Crée le `Poll`, les `TimeSlot` et les `Participant`
   - Génère un token unique par participant
   - Envoie un email d'invitation à chaque participant contenant son lien personnel

#### 3.2.2 Modification

- Le créateur peut modifier le sondage tant qu'il est actif
- Modification du titre, description, lieu, deadline
- Ajout/suppression de créneaux (attention : supprimer un créneau supprime les votes associés — confirmation requise)
- Ajout de nouveaux participants (envoi automatique d'email)
- Suppression de participants (supprime leurs votes)

#### 3.2.3 Clôture

- **Automatique** : une tâche planifiée vérifie périodiquement les sondages dont la `deadline` est dépassée et les marque comme clôturés
- **Manuelle** : le créateur peut clôturer à tout moment via un bouton
- À la clôture, `closed_at` est renseigné
- Les participants ne peuvent plus modifier leurs votes après clôture

#### 3.2.4 Choix du créneau final

- Après clôture (ou avant, au choix du créateur), celui-ci peut sélectionner le créneau retenu
- Cette action déclenche l'envoi d'un email de notification à tous les participants, indiquant le créneau choisi

#### 3.2.5 Suppression automatique

- Une tâche planifiée supprime les sondages dont `closed_at + retention_days` est dépassé
- La valeur de `retention_days` est lue depuis `SiteConfiguration`

### 3.3 Participation (vote)

#### 3.3.1 Accès

- Le participant accède au sondage via son lien unique : `/poll/<poll_id>/vote/<token>/`
- Aucune authentification requise — le token fait office d'identification
- Si le sondage est actif : affichage de l'interface de vote
- Si le sondage est clôturé : affichage en lecture seule (le participant voit ses votes et le résultat)

#### 3.3.2 Interface de vote

- Affichage des créneaux dans une vue calendrier (voir §4)
- Chaque créneau est représenté comme un bloc coloré
- Le participant clique sur une des trois icônes pour chaque créneau :
  - ✓ (Oui) → bloc vert
  - ? (Peut-être) → bloc orange
  - ✗ (Non) → bloc rouge
- Couleur par défaut (pas encore voté) : gris
- Un bouton de soumission enregistre tous les votes en une fois
- Le participant peut revenir et modifier ses votes tant que le sondage est actif

#### 3.3.3 Résumé anonymisé

- Sous le calendrier (ou dans un panneau dédié), le participant voit un récapitulatif par créneau :
  - Nombre de « Oui »
  - Nombre de « Peut-être »
  - Nombre de « Non »
  - Nombre de non-répondants
  - Score pondéré du créneau (voir §2.6)
- Aucun nom n'est affiché — les compteurs sont anonymes
- Les créneaux sont triés par score décroissant

### 3.4 Vue créateur (récapitulatif)

- Le créateur accède à une vue détaillée de chaque sondage qu'il a créé
- **Tableau récapitulatif** : lignes = participants, colonnes = créneaux (triés par score décroissant, voir §2.6), cellules = choix (colorées)
- Indication visuelle du/des créneau(x) ayant le meilleur score (mise en évidence)
- Affichage du score de chaque créneau dans l'en-tête de colonne
- Liste des participants n'ayant pas encore voté (pour relance)
- Bouton « Relancer les non-répondants » → envoie un email de rappel aux participants dont `has_voted` est False
- Bouton « Clôturer le sondage »
- Bouton/mécanisme pour sélectionner le créneau final

### 3.5 Liste des sondages (créateur)

- Page listant tous les sondages du créateur authentifié
- Affichage simple : titre, date de création, deadline, statut (actif/clôturé), nombre de réponses
- Lien vers la vue détaillée de chaque sondage
- Bouton de création d'un nouveau sondage

---

## 4. Interface calendrier (composant FullCalendar)

Le calendrier est le composant central de l'interface, utilisé à la fois pour la création des créneaux (côté créateur) et pour le vote (côté participant).

### 4.1 Bibliothèque

Utiliser **FullCalendar** (version open-source, CDN) avec les plugins nécessaires :
- `dayGrid` (vue mois)
- `timeGrid` (vue semaine)
- `interaction` (sélection, drag, resize)

### 4.2 Mode création (créateur)

- Vues disponibles : semaine et mois, avec bascule
- **Clic-glisser** sur une plage horaire pour créer un créneau
- Les créneaux créés sont affichés en **gris**
- Chaque créneau est **déplaçable** (drag & drop) et **redimensionnable**
- Chaque créneau affiche une **icône de suppression** (×) au survol ou au clic, ou suppression via touche Delete après sélection
- Les données des créneaux sont stockées côté client (JS) et envoyées au serveur à la soumission du formulaire (champ hidden JSON ou requête AJAX)

### 4.3 Mode vote (participant)

- Vues disponibles : semaine et mois, avec bascule
- Les créneaux sont affichés comme des blocs **non déplaçables et non redimensionnables**
- Chaque bloc affiche **trois icônes** cliquables :
  - ✓ (Oui)
  - ? (Peut-être)
  - ✗ (Non)
- Au clic sur une icône, la **couleur du bloc change** :
  - Gris → pas encore voté (défaut)
  - Vert → Oui
  - Orange → Peut-être
  - Rouge → Non
- L'icône active est visuellement mise en évidence (ex: contour, taille, opacité)
- Les votes sont envoyés au serveur via un bouton « Enregistrer mes disponibilités »

### 4.4 Mode lecture seule (sondage clôturé)

- Même affichage que le mode vote, mais sans les icônes de vote
- Les créneaux sont colorés selon le vote du participant
- Le créneau retenu (si défini) est mis en évidence (bordure, badge, couleur distincte)

### 4.5 Responsive

- Sur mobile, le calendrier bascule automatiquement en vue liste (`listWeek`) ou en vue jour (`timeGridDay`) pour une meilleure lisibilité
- Les icônes de vote doivent être suffisamment grandes pour être utilisables au doigt (min 44×44px de zone de tap)

---

## 5. Emails

Tous les emails sont envoyés via les paramètres SMTP configurés dans `SiteConfiguration`. L'envoi doit utiliser un backend email Django personnalisé ou une fonction utilitaire qui lit la configuration dynamiquement à chaque envoi.

### 5.1 Templates email

Tous les emails sont en HTML avec fallback texte brut, en français. Ils intègrent le logo et les couleurs de la charte graphique issus de `SiteConfiguration`.

| Email | Destinataire | Déclencheur | Contenu |
|---|---|---|---|
| **Invitation** | Participant | Création du sondage / ajout de participant | Titre du sondage, description, lien personnel de vote |
| **Rappel** | Participant (non-répondant) | Clic « Relancer » par le créateur | Rappel avec lien personnel, mention de la deadline |
| **Choix final** | Tous les participants | Sélection du créneau retenu | Créneau retenu (date, heure, lieu), lien de consultation |
| **Reset mot de passe** | Créateur | Demande de reset | Lien de réinitialisation (mécanisme Django standard) |

---

## 6. Architecture technique

### 6.1 Stack

| Composant | Technologie |
|---|---|
| Backend | Django 5.x |
| Serveur WSGI | Gunicorn |
| Base de données | SQLite (fichier monté en volume Docker) |
| Fichiers statiques | WhiteNoise |
| Tâches planifiées | django-apscheduler |
| Calendrier | FullCalendar (CDN) |
| Frontend | Django Templates + CSS custom + vanilla JS |
| Conteneurisation | Docker + Docker Compose |
| Accès externe | Cloudflare Tunnel (cloudflared, hors scope Docker) |

### 6.2 Structure du projet

```
django-meeting/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example            # Variables d'environnement documentées
├── .gitignore
├── README.md               # Documentation d'installation et d'utilisation
├── manage.py
├── config/                  # Projet Django (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── polls/               # App principale (sondages)
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   ├── admin.py
│   │   ├── tasks.py         # Tâches planifiées (clôture auto, purge)
│   │   ├── email.py         # Utilitaires d'envoi d'email dynamique
│   │   ├── tokens.py        # Génération de tokens
│   │   └── templatetags/    # Filtres/tags custom si nécessaire
│   ├── accounts/            # App authentification créateurs
│   │   ├── views.py         # Login, logout, password reset
│   │   ├── urls.py
│   │   └── forms.py
│   └── site_config/         # App configuration du site (singleton)
│       ├── models.py
│       ├── admin.py
│       └── context_processors.py  # Injecte la config dans tous les templates
├── templates/
│   ├── base.html            # Template de base (charte graphique dynamique)
│   ├── polls/
│   │   ├── poll_list.html
│   │   ├── poll_create.html
│   │   ├── poll_detail.html # Vue récapitulatif créateur
│   │   ├── poll_vote.html   # Interface de vote participant
│   │   └── poll_closed.html # Vue lecture seule
│   ├── accounts/
│   │   ├── login.html
│   │   └── password_reset*.html
│   └── emails/
│       ├── invitation.html
│       ├── reminder.html
│       └── final_choice.html
├── static/
│   ├── css/
│   │   └── style.css        # Styles custom (utilise les CSS variables de la charte)
│   └── js/
│       ├── calendar_create.js  # Logique FullCalendar mode création
│       └── calendar_vote.js    # Logique FullCalendar mode vote
├── media/                   # Fichiers uploadés (logo)
└── docs/
    ├── SPEC.md              # Ce fichier
    └── CLAUDE.md            # Instructions pour Claude Code
```

### 6.3 Configuration Django

- `SECRET_KEY` : via variable d'environnement
- `DEBUG` : via variable d'environnement (défaut: False)
- `ALLOWED_HOSTS` : via variable d'environnement (séparés par virgule)
- `DATABASE` : SQLite, chemin configurable via variable d'environnement (défaut en dev : `BASE_DIR / "db.sqlite3"`, en Docker : `/data/db.sqlite3`)
- `STATIC_URL` / `STATIC_ROOT` : configurés pour WhiteNoise
- `MEDIA_URL` / `MEDIA_ROOT` : pour les uploads (logo)
- `TIME_ZONE` : `Europe/Brussels`
- `LANGUAGE_CODE` : `fr-fr`
- Les paramètres email ne sont **pas** dans les settings — ils sont gérés par `SiteConfiguration`

### 6.4 Docker

#### Dockerfile

- Image de base : `python:3.12-slim`
- Installation des dépendances via `requirements.txt`
- `collectstatic` exécuté au build
- Entrypoint : `gunicorn config.wsgi:application --bind 0.0.0.0:8768`

#### docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "8768:8768"
    volumes:
      - ./db_data:/data          # SQLite (dossier relatif au docker-compose)
      - ./media_data:/app/media  # Logo uploadé (dossier relatif au docker-compose)
    env_file:
      - .env
    restart: unless-stopped
```

Les dossiers `db_data/` et `media_data/` sont des **bind mounts relatifs** au répertoire du `docker-compose.yml`. Ils sont créés automatiquement par Docker s'ils n'existent pas, et doivent figurer dans le `.gitignore`.

Un fichier `.env.example` doit être fourni avec toutes les variables documentées.

### 6.5 Mode développement (hors Docker)

Le projet doit rester testable de manière classique pendant le développement :

```bash
python manage.py migrate
python manage.py runserver
```

Pour cela :
- `config/settings.py` doit fonctionner **sans variable d'environnement** grâce à des valeurs par défaut sensées pour le développement :
  - `SECRET_KEY` : valeur par défaut en dur (uniquement si `DEBUG=True`)
  - `DEBUG` : `True` par défaut
  - `ALLOWED_HOSTS` : `["*"]` si `DEBUG=True`
  - `DATABASE` : SQLite dans `BASE_DIR / "db.sqlite3"` par défaut (le chemin `/data/db.sqlite3` est utilisé uniquement en Docker via variable d'env)
  - `MEDIA_ROOT` : `BASE_DIR / "media"` par défaut
- WhiteNoise doit être compatible avec `runserver` (middleware activé dans tous les cas)
- Les emails en mode développement : si `SiteConfiguration` n'a pas de SMTP configuré, fallback sur le backend console Django (`django.core.mail.backends.console.EmailBackend`)

### 6.6 Tâches planifiées (django-apscheduler)

Deux tâches enregistrées au démarrage de l'application :

| Tâche | Fréquence | Action |
|---|---|---|
| `close_expired_polls` | Toutes les 5 minutes | Clôture les sondages dont `deadline < now()` et `is_closed = False` |
| `purge_old_polls` | Une fois par jour (3h du matin) | Supprime les sondages dont `closed_at + retention_days` est dépassé |

---

## 7. URLs

### 7.1 Authentification (créateurs)

| URL | Vue | Description |
|---|---|---|
| `/login/` | LoginView | Connexion |
| `/logout/` | LogoutView | Déconnexion |
| `/password-reset/` | PasswordResetView | Demande de reset |
| `/password-reset/done/` | PasswordResetDoneView | Confirmation envoi |
| `/reset/<uidb64>/<token>/` | PasswordResetConfirmView | Formulaire nouveau MDP |
| `/reset/done/` | PasswordResetCompleteView | Confirmation reset |

### 7.2 Sondages (créateurs authentifiés)

| URL | Vue | Description |
|---|---|---|
| `/` | `poll_list` | Liste des sondages du créateur |
| `/poll/create/` | `poll_create` | Formulaire de création |
| `/poll/<uuid:pk>/` | `poll_detail` | Vue détaillée / récapitulatif |
| `/poll/<uuid:pk>/edit/` | `poll_edit` | Modification du sondage |
| `/poll/<uuid:pk>/close/` | `poll_close` | Clôture manuelle (POST) |
| `/poll/<uuid:pk>/choose/<uuid:slot_id>/` | `poll_choose_slot` | Sélection créneau final (POST) |
| `/poll/<uuid:pk>/remind/` | `poll_remind` | Relance non-répondants (POST) |
| `/poll/<uuid:pk>/delete/` | `poll_delete` | Suppression (avec confirmation) |

### 7.3 Participation (accès par token)

| URL | Vue | Description |
|---|---|---|
| `/poll/<uuid:poll_id>/vote/<str:token>/` | `poll_vote` | Interface de vote |
| `/poll/<uuid:poll_id>/vote/<str:token>/submit/` | `poll_vote_submit` | Soumission des votes (POST) |

### 7.4 API interne (AJAX)

| URL | Méthode | Description |
|---|---|---|
| `/api/poll/<uuid:pk>/summary/` | GET | Compteurs anonymisés et score pondéré par créneau (JSON) |

---

## 8. Sécurité

- Les tokens participants sont générés avec `secrets.token_urlsafe(48)` (cryptographiquement sûrs)
- Les vues créateur sont protégées par `@login_required` et vérifient que `poll.creator == request.user`
- Les vues participant vérifient la validité du token et l'appartenance au sondage
- Protection CSRF sur tous les formulaires
- Le mot de passe SMTP en base est chiffré (ex: `django-fernet-fields` ou équivalent)
- Rate limiting conseillé sur les endpoints email (relance) pour éviter les abus
- Les UUID dans les URLs empêchent l'énumération séquentielle

---

## 9. Charte graphique dynamique

Le template `base.html` injecte les couleurs de `SiteConfiguration` en tant que CSS custom properties :

```html
<style>
  :root {
    --color-primary: {{ site_config.primary_color }};
    --color-secondary: {{ site_config.secondary_color }};
  }
</style>
```

Tous les styles de `style.css` utilisent ces variables. Cela permet de changer l'apparence de l'application sans toucher au code.

Le logo est affiché dans le header via `{{ site_config.logo.url }}` si défini.

---

## 10. Dépendances Python

```
Django>=5.0,<6.0
gunicorn
whitenoise
django-apscheduler
django-solo            # Modèle singleton pour SiteConfiguration
Pillow                 # Upload d'images (logo)
```
