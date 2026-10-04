# Open WebUI Tools

Une petite collection d'outils pour [Open WebUI](https://github.com/open-webui/open-webui) :
Gmail, Google Calendar, et un filtre OpenRouter ZDR.

Tout est en Python pur. Pas de serveur MCP, pas de service relais, pas de
Docker — les outils appellent directement les API Google avec `httpx` et des
refresh tokens OAuth2. Tu copies les fichiers dans `tools/`, tu redémarres
Open WebUI, tu remplis les Valves.

## Outils

| Outil | Fichier | Ce qu'il fait |
| --- | --- | --- |
| Gmail | [`tools/gmail.py`](tools/gmail.py) | Lister, chercher, lire, rédiger, envoyer, répondre, archiver, étiqueter et supprimer des emails |
| Google Calendar | [`tools/google-calendar.py`](tools/google-calendar.py) | Consulter, chercher, créer, modifier et supprimer des événements, sur plusieurs calendriers |
| OpenRouter ZDR | [`tools/openrouter_zdr.py`](tools/openrouter_zdr.py) | Force `provider.zdr = true` sur chaque requête OpenRouter |

Les deux outils Google partagent la même mécanique : un Client ID OAuth2, un
secret, et un refresh token longue durée, le tout stocké dans les Valves de
l'outil (`Workspace → Tools → <outil>`).

## Installation

```bash
cd /chemin/vers/open-webui/backend/open_webui/tools
cp /chemin/vers/ce/repo/tools/*.py .
```

Redémarre Open WebUI. Les outils apparaissent dans **Workspace → Tools**, et
leurs Valves dans **Tools → <nom>**.

Chaque outil déclare ses propres dépendances dans l'en-tête de sa docstring,
lue par Open WebUI au chargement :

- `gmail.py` → `httpx>=0.27`
- `google-calendar.py` → `httpx>=0.27`
- `openrouter_zdr.py` → rien (pydantic uniquement)

## Configuration OAuth2 (Gmail & Calendar)

Les deux utilisent les mêmes identifiants ; seuls les scopes diffèrent.
Récupérer un refresh token prend environ cinq minutes, une seule fois.

### 1. Créer le client OAuth

Dans la [Google Cloud Console](https://console.cloud.google.com) :

- **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
- Type d'application : **Web application**
- URI de redirection autorisé : `https://developers.google.com/oauthplayground`

### 2. Activer les API nécessaires

- **APIs & Services → Library → "Gmail API" → Enable**
- **APIs & Services → Library → "Google Calendar API" → Enable**

### 3. Obtenir un refresh token

Sur le [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) :

1. Icône engrenage (en haut à droite) → *Use your own OAuth credentials* →
   colle ton Client ID et ton Client Secret.
2. **Step 1** — saisis le scope :
   - `https://mail.google.com/` pour Gmail
   - `https://www.googleapis.com/auth/calendar` pour Calendar
   - ou les deux, séparés par une espace, si tu veux un seul refresh token
     pour les deux outils
3. **Authorize APIs** et connecte-toi avec le compte Google que tu veux exposer.
4. **Step 2** — *Exchange authorization code for tokens*.
5. Copie le **Refresh token**.

### 4. Remplir les Valves

| Valve | Remarques |
| --- | --- |
| `CLIENT_ID` | Client ID OAuth2 |
| `CLIENT_SECRET` | Client Secret OAuth2 |
| `REFRESH_TOKEN` | Celui de l'étape 3.5 |
| `DEFAULT_MAX_RESULTS` / `MAX_RESULTS` | Taille de page pour les appels liste/recherche |
| `REQUEST_TIMEOUT` | Timeout HTTP en secondes (`15.0` par défaut) |
| `DEFAULT_TIMEZONE` | Calendar uniquement — timezone IANA pour les événements créés |
| `DEFAULT_CALENDAR_ID` | Calendar uniquement — `primary` pour le calendrier principal |
| `CALENDARS_TO_WATCH` | Calendar uniquement — IDs de calendriers supplémentaires, séparés par des virgules |

Le refresh token est aussi sensible qu'un mot de passe : quiconque le détient
peut agir sur le compte tant qu'il n'est pas révoqué. Pour le révoquer :
[Google Account → Security → Third-party access](https://myaccount.google.com/connections).

## Utilisation

### Gmail

| Méthode | Description |
| --- | --- |
| `check_auth_status()` | Confirme la connexion et renvoie l'adresse de la boîte |
| `get_unread_count()` | Nombre de non-lus dans la boîte de réception, sans lire le contenu |
| `list_recent_emails(max_results, label)` | Messages récents de `INBOX`, `SENT`, `DRAFTS`, `SPAM`, `STARRED`, `UNREAD`, `TRASH` |
| `search_emails(query, max_results)` | Syntaxe de recherche Gmail (`from:`, `subject:`, `has:attachment`, `after:` …) |
| `get_email_content(message_id)` | Corps complet d'un message |
| `send_email(to, subject, body, cc, bcc)` | Envoie un message |
| `reply_to_email(message_id, body, reply_all)` | Répond dans le fil d'origine |
| `create_draft(to, subject, body)` | Enregistre un brouillon sans l'envoyer |
| `archive_email(message_id)` | Retire le label `INBOX` |
| `delete_email(message_id)` | Met à la corbeille |
| `mark_as_read` / `mark_as_unread` | Bascule le label `UNREAD` |
| `add_label(message_id, label)` | Ajoute un label |

### Google Calendar

| Méthode | Description |
| --- | --- |
| `check_auth_status()` | Vérifie le token et liste les calendriers accessibles |
| `list_calendars()` | IDs de tous les calendriers visibles par le compte |
| `list_upcoming_events(max_results, calendar_id)` | Prochains événements |
| `search_events(query, time_min, time_max, max_results, calendar_id)` | Recherche plein texte sur une fenêtre de dates |
| `get_event_details(event_id, calendar_id)` | Un événement en détail |
| `create_event(summary, start_datetime, end_datetime, …)` | Crée un événement, avec description, lieu et participants |
| `quick_add_event(text)` | En langage naturel, par ex. *"Dentiste mardi 15:00"* |
| `update_event(event_id, …)` | Mise à jour partielle — seuls les champs passés sont touchés |
| `delete_event(event_id)` | Supprime un événement |

Les dates sont en ISO 8601 (`2026-10-04T15:00:00+02:00`) ; `create_event`
accepte aussi `all_day=True` avec des bornes en `YYYY-MM-DD`.

### OpenRouter ZDR

Un filtre avec une seule Valve, `ZDR_ENABLED` (`true` par défaut). Quand elle
est active, il ajoute `provider: { zdr: true }` au body de chaque requête,
pour qu'OpenRouter ne route uniquement que vers des providers en Zero Data
Retention. Si ton offre OpenRouter ne gère pas le ZDR, les requêtes échoueront
— désactive alors la Valve.

## Prompter correctement

Les docstrings de Gmail demandent déjà au modèle de confirmer avant de lire une
boîte mail, mais un modèle peut toujours être convaincu de passer outre. Si
cette limite compte pour toi, écris-la dans un system prompt :

> Avant tout appel à un outil Gmail ou Calendar, demande-moi confirmation et
> attends un « oui » explicite. N'envoie, ne supprime et ne modifie rien à la
> première demande.

Tout ce que fait le modèle passe par ton propre compte Google. Révoquer
l'accès est le moyen le plus rapide de l'arrêter.

## Licence

**Non commercial + attribution.** Voir [LICENSE](LICENSE).

Usage personnel, recherche et évaluation : autorisé. Usage commercial,
revente, ou intégration dans un produit payant : soumis à autorisation écrite
de l'auteur, avec crédit.

Les contributions sont bienvenues, mais tu conserves ton copyright et tu es
crédité comme contributeur.

## Contribuer

Issues et pull requests bienvenues. Respecte le style existant : docstrings
en français, identifiants en anglais, `httpx` seulement, aucune nouvelle
dépendance runtime.

En contribuant, tu acceptes que ta contribution soit publiée sous les mêmes
termes, et tu seras crédité comme contributeur.

## Auteur

Anas — [GitHub](https://github.com/anas)