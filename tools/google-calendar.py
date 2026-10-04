"""
title: Google Calendar
author: Ahmed
description: >-
  Permet au LLM de consulter, créer, modifier et supprimer des événements
  Google Calendar. Appel direct vers l'API Google — aucun serveur relay,
  aucun Docker. Authentification via OAuth2 refresh_token (configurable
  dans les Valves).
required_open_webui_version: 0.4.0
requirements: httpx>=0.27
version: 1.1.0
licence: MIT
"""

# =============================================================================
# Google Calendar — Tool Open WebUI (appel direct API Google)
# =============================================================================
#
# ARCHITECTURE :
#   Open WebUI -> Ce Tool (httpx) -> Google Calendar API v3
#
# AUTHENTIFICATION (à faire une seule fois) :
#   1. Aller sur https://developers.google.com/oauthplayground
#   2. Cliquer (Settings) (Settings) -> cocher "Use your own OAuth credentials"
#      -> entrer ton Client ID et Client Secret
#   3. Dans "Step 1", chercher "Google Calendar API v3"
#      -> sélectionner "https://www.googleapis.com/auth/calendar"
#      -> "Authorize APIs" -> se connecter avec son compte Google
#   4. "Step 2" -> "Exchange authorization code for tokens"
#   5. Copier le "Refresh token" -> le coller dans la Valve REFRESH_TOKEN
#
# =============================================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import httpx
from pydantic import BaseModel, Field


def _plural(n: int, mot: str) -> str:
    """Accord en nombre, sans le "(s)" disgracieux."""
    return f"{n} {mot}" if n <= 1 else f"{n} {mot}s"


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"


class Tools:
    """
    Tool Open WebUI pour gérer Google Calendar.

    Consulte, crée, modifie et supprime des événements Google Calendar
    directement via l'API Google, sans serveur intermédiaire.
    """

    class Valves(BaseModel):
        """
        Reglages admin — Workspace -> Tools -> Google Calendar -> Valves.

        Les trois premiers champs (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN)
        sont obligatoires. Voir les instructions en haut de ce fichier
        pour les obtenir en 5 minutes via OAuth2 Playground.
        """

        CLIENT_ID: str = Field(
            default="",
            description=(
                "Client ID OAuth2 Google. "
                "console.cloud.google.com -> Identifiants -> OAuth 2.0."
            ),
        )
        CLIENT_SECRET: str = Field(
            default="",
            description="Client Secret OAuth2 Google.",
        )
        REFRESH_TOKEN: str = Field(
            default="",
            description=(
                "Refresh token OAuth2 (permanent). "
                "Obtenir via https://developers.google.com/oauthplayground"
            ),
        )
        DEFAULT_TIMEZONE: str = Field(
            default="Europe/Paris",
            description="Timezone IANA pour les événements créés.",
        )
        DEFAULT_CALENDAR_ID: str = Field(
            default="primary",
            description=(
                "Calendrier par défaut. 'primary' = calendrier principal. "
                "Utiliser list_calendars() pour voir les autres IDs."
            ),
        )
        MAX_RESULTS: int = Field(
            default=20,
            description="Nombre max d'événements retournés par les listes.",
        )
        REQUEST_TIMEOUT: float = Field(
            default=15.0,
            description="Timeout HTTP en secondes.",
        )
        CALENDARS_TO_WATCH: str = Field(
            default="",
            description=(
                "IDs des calendriers a interroger en parallele dans "
                "list_upcoming_events et search_events. "
                "Separer par des virgules. "
                "Laisser vide = seulement DEFAULT_CALENDAR_ID. "
                "Exemple : primary,bc1c8c4dac1e3406...@group.calendar.google.com"
            ),
        )

    def __init__(self) -> None:
        self.valves = self.Valves()
        self.citation = False
        # Cache de l'access_token en mémoire (durée de vie ~1h côté Google)
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    # ================================================================= Auth

    async def _get_access_token(self) -> str:
        """
        Retourne un access_token valide. Le rafraîchit automatiquement
        via le refresh_token si expiré ou absent.
        """
        import time

        # Marge de 60s pour éviter d'utiliser un token sur le point d'expirer
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        if not self.valves.CLIENT_ID:
            raise RuntimeError(
                "CLIENT_ID manquant dans les Valves. "
                "Configurer CLIENT_ID, CLIENT_SECRET et REFRESH_TOKEN."
            )
        if not self.valves.REFRESH_TOKEN:
            raise RuntimeError(
                "REFRESH_TOKEN manquant dans les Valves. "
                "Voir les instructions en haut du fichier Tool."
            )

        async with httpx.AsyncClient(timeout=self.valves.REQUEST_TIMEOUT) as client:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.valves.CLIENT_ID,
                    "client_secret": self.valves.CLIENT_SECRET,
                    "refresh_token": self.valves.REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Impossible de rafraîchir le token Google "
                f"(HTTP {resp.status_code}) : {resp.text[:300]}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._access_token

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ============================================================= Helpers

    async def _emit(
        self,
        emitter: Optional[Callable[[dict], Awaitable[None]]],
        msg: str,
        done: bool = False,
    ) -> None:
        # [2026-09-28] passed checks - desactive sur demande explicite, meme
        # traitement que recall_tool.py/ultra.py/atc.py/gmail.py le meme jour.
        return

    async def _api(
        self,
        method: str,
        path: str,
        emitter=None,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """Appel générique vers l'API Google Calendar."""
        token = await self._get_access_token()
        url = f"{GOOGLE_CALENDAR_BASE}{path}"

        async with httpx.AsyncClient(timeout=self.valves.REQUEST_TIMEOUT) as client:
            resp = await client.request(
                method,
                url,
                headers=self._auth_headers(token),
                json=json_body,
                params={k: v for k, v in (params or {}).items() if v is not None},
            )

        if resp.status_code == 204:
            return {}

        if resp.status_code >= 400:
            detail = resp.text[:400]
            raise RuntimeError(
                f"Google Calendar API — HTTP {resp.status_code} : {detail}"
            )

        return resp.json()

    def _fmt_event(self, e: dict) -> str:
        """Formate un événement en texte lisible pour le LLM."""
        title = e.get("summary") or "(sans titre)"
        start = e.get("start", {})
        end = e.get("end", {})
        start_str = start.get("dateTime") or start.get("date") or "?"
        end_str = end.get("dateTime") or end.get("date") or "?"
        all_day = "date" in start and "dateTime" not in start

        lines = [f"**{title}**"]
        if all_day:
            lines.append(f"   Journee entiere : {start_str} -> {end_str}")
        else:
            lines.append(f"   Debut    : {start_str}")
            lines.append(f"   Fin      : {end_str}")
        # Afficher le calendrier source quand il est renseigne (multi-cal)
        if e.get("_calendar_id"):
            lines.append(f"   Agenda   : {e['_calendar_id']}")
        if e.get("location"):
            lines.append(f"   Lieu     : {e['location']}")
        if e.get("description"):
            lines.append(f"   Note     : {e['description'][:300]}")
        attendees = e.get("attendees", [])
        if attendees:
            emails = [a.get("email", "?") for a in attendees]
            lines.append(f"   Invites  : {', '.join(emails)}")
        lines.append(f"   ID       : `{e.get('id', '?')}`")
        if e.get("htmlLink"):
            lines.append(f"   Lien     : {e['htmlLink']}")
        return "\n".join(lines)

    def _fmt_events(self, events: list[dict]) -> str:
        if not events:
            return "Aucun événement trouvé."
        return "\n\n".join(self._fmt_event(e) for e in events)

    def _sort_key(self, e: dict) -> str:
        """Cle de tri : dateTime ou date, pour fusionner plusieurs calendriers."""
        s = e.get("start", {})
        return s.get("dateTime") or s.get("date") or ""

    def _get_calendar_ids(self, override: str = "") -> list[str]:
        """
        Retourne la liste des IDs a interroger.
        Priorite : parametre override > CALENDARS_TO_WATCH > DEFAULT_CALENDAR_ID.
        """
        if override:
            return [c.strip() for c in override.split(",") if c.strip()]
        if self.valves.CALENDARS_TO_WATCH:
            return [
                c.strip()
                for c in self.valves.CALENDARS_TO_WATCH.split(",")
                if c.strip()
            ]
        return [self.valves.DEFAULT_CALENDAR_ID or "primary"]

    # ======================================== Méthodes exposées au LLM

    async def list_upcoming_events(
        self,
        max_results: int = 10,
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Liste les prochains événements à venir sur TOUS les calendriers
        configures dans CALENDARS_TO_WATCH (ou le calendrier par défaut).
        Les résultats de tous les agendas sont fusionnes et tries par heure.
        A utiliser quand l'utilisateur demande : "qu'est-ce que j'ai de
        prévu ?", "montre-moi mon agenda", "quels sont mes prochains
        rendez-vous ?", "qu'est-ce que j'ai aujourd'hui ?".

        :param max_results: Nombre total d'événements a retourner (1-100).
        :param calendar_id: Forcer un calendrier specifique (vide = tous ceux
            configures dans CALENDARS_TO_WATCH).
        :return: Liste fusionnee et triee des événements à venir.
        """
        import asyncio

        cal_ids = self._get_calendar_ids(calendar_id)
        await self._emit(
            __event_emitter__,
            f"Lecture · {_plural(len(cal_ids), 'agenda')}",
        )
        now = datetime.now(timezone.utc).isoformat()
        # On prend plus d'evenements par calendrier pour avoir un bon merge
        per_cal = max(max_results, 50)

        async def fetch_one(cal: str) -> list[dict]:
            try:
                data = await self._api(
                    "GET",
                    f"/calendars/{cal}/events",
                    None,  # pas d'emitter par calendrier individuel
                    params={
                        "timeMin": now,
                        "maxResults": per_cal,
                        "singleEvents": "true",
                        "orderBy": "startTime",
                    },
                )
                items = data.get("items", [])
                # Annoter chaque evenement avec son calendrier source
                for item in items:
                    item["_calendar_id"] = cal
                return items
            except RuntimeError:
                return []

        results = await asyncio.gather(*[fetch_one(c) for c in cal_ids])

        # Fusion + tri + deduplication par ID
        seen_ids: set[str] = set()
        all_events: list[dict] = []
        for batch in results:
            for e in batch:
                eid = e.get("id", "")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    all_events.append(e)

        all_events.sort(key=self._sort_key)
        all_events = all_events[:max_results]

        total = len(all_events)
        await self._emit(
            __event_emitter__,
            f"{_plural(total, 'événement')} · {_plural(len(cal_ids), 'agenda')}",
            done=True,
        )
        return self._fmt_events(all_events)

    async def search_events(
        self,
        query: str = "",
        time_min: str = "",
        time_max: str = "",
        max_results: int = 20,
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Recherche des événements par mot-clé et/ou plage de dates sur TOUS
        les calendriers configures dans CALENDARS_TO_WATCH. Les résultats
        sont fusionnes et tries par heure.
        A utiliser pour : "est-ce que j'ai un rendez-vous chez le dentiste ?",
        "quels événements ai-je la semaine prochaine ?", "trouve les réunions
        de mai 2026".

        :param query: Mot-clé à chercher dans le titre/description/lieu.
        :param time_min: Début de la plage ISO 8601, ex: 2026-05-01T00:00:00+02:00.
        :param time_max: Fin de la plage ISO 8601.
        :param max_results: Nombre max de résultats totaux.
        :param calendar_id: Forcer un calendrier specifique (vide = tous).
        :return: Liste fusionnee des événements correspondants.
        """
        import asyncio

        cal_ids = self._get_calendar_ids(calendar_id)
        label = f" '{query}'" if query else ""
        await self._emit(
            __event_emitter__, f"Recherche{label} · {_plural(len(cal_ids), 'agenda')}"
        )

        base_params: dict = {
            "maxResults": min(max_results * 2, 100),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        if query:
            base_params["q"] = query
        base_params["timeMin"] = (
            time_min if time_min else datetime.now(timezone.utc).isoformat()
        )
        if time_max:
            base_params["timeMax"] = time_max

        async def fetch_one(cal: str) -> list[dict]:
            try:
                data = await self._api(
                    "GET", f"/calendars/{cal}/events", None, params=dict(base_params)
                )
                items = data.get("items", [])
                for item in items:
                    item["_calendar_id"] = cal
                return items
            except RuntimeError:
                return []

        results = await asyncio.gather(*[fetch_one(c) for c in cal_ids])

        seen_ids: set[str] = set()
        all_events: list[dict] = []
        for batch in results:
            for e in batch:
                eid = e.get("id", "")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    all_events.append(e)

        all_events.sort(key=self._sort_key)
        all_events = all_events[:max_results]

        await self._emit(
            __event_emitter__, f"{_plural(len(all_events), 'résultat')}", done=True
        )
        return self._fmt_events(all_events)

    async def get_event_details(
        self,
        event_id: str,
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Récupère les détails complets d'un événement par son ID.
        À utiliser quand l'utilisateur a un ID d'événement et veut des
        informations complètes (description, invités, lien, récurrence).

        :param event_id: Identifiant Google de l'événement.
        :param calendar_id: ID du calendrier (vide = par défaut).
        :return: Détails complets de l'événement.
        """
        await self._emit(__event_emitter__, "Récupération de l'événement")
        cal = calendar_id or self.valves.DEFAULT_CALENDAR_ID

        try:
            event = await self._api(
                "GET", f"/calendars/{cal}/events/{event_id}", __event_emitter__
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur : {exc}"

        await self._emit(__event_emitter__, "Événement récupéré", done=True)
        return self._fmt_event(event)

    async def create_event(
        self,
        summary: str,
        start_datetime: str,
        end_datetime: str,
        description: str = "",
        location: str = "",
        attendees: str = "",
        all_day: bool = False,
        send_updates: str = "none",
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Crée un nouvel événement dans Google Calendar.
        À utiliser quand l'utilisateur veut planifier quelque chose :
        "ajoute un rendez-vous", "programme une réunion", "mets un
        rappel lundi à 14h".

        :param summary: Titre de l'événement (obligatoire).
        :param start_datetime: Début au format ISO 8601 avec timezone.
            Exemples : "2026-05-10T14:00:00+02:00" (avec heure),
            ou "2026-05-10" si all_day=True.
        :param end_datetime: Fin au format ISO 8601. Pour un événement
            journée entière, mettre le jour suivant : "2026-05-11".
        :param description: Description de l'événement.
        :param location: Lieu (adresse ou nom de salle).
        :param attendees: Emails des invités séparés par des virgules.
            Exemple : "alice@gmail.com, bob@gmail.com".
        :param all_day: True pour un événement sur toute la journée.
        :param send_updates: "all" pour notifier les invités par email,
            "none" pour ne pas notifier.
        :param calendar_id: ID du calendrier cible (vide = par défaut).
        :return: Confirmation avec les détails de l'événement créé.
        """
        await self._emit(__event_emitter__, f"Création · {summary}")
        cal = calendar_id or self.valves.DEFAULT_CALENDAR_ID
        tz = self.valves.DEFAULT_TIMEZONE

        body: dict = {"summary": summary}
        if description:
            body["description"] = description
        if location:
            body["location"] = location

        if all_day:
            body["start"] = {"date": start_datetime[:10]}
            body["end"] = {"date": end_datetime[:10]}
        else:
            body["start"] = {"dateTime": start_datetime, "timeZone": tz}
            body["end"] = {"dateTime": end_datetime, "timeZone": tz}

        if attendees:
            body["attendees"] = [
                {"email": e.strip()} for e in attendees.split(",") if e.strip()
            ]

        try:
            event = await self._api(
                "POST",
                f"/calendars/{cal}/events",
                __event_emitter__,
                json_body=body,
                params={"sendUpdates": send_updates},
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur lors de la création : {exc}"

        await self._emit(__event_emitter__, "Événement créé", done=True)
        return "Evenement cree avec succes :\n\n" + self._fmt_event(event)

    async def quick_add_event(
        self,
        text: str,
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Crée un événement via une description en langage naturel.
        Google parse automatiquement le texte pour extraire la date,
        l'heure et le titre. À utiliser pour des ajouts rapides et
        informels comme : "Dentiste vendredi 15h", "Réunion d'équipe
        lundi 10h au bureau", "Anniversaire de Papa le 20 mai".

        Préférer create_event() si tu veux contrôler précisément les champs.

        :param text: Description en langage naturel de l'événement.
        :param calendar_id: ID du calendrier (vide = par défaut).
        :return: Confirmation avec les détails de l'événement créé.
        """
        await self._emit(__event_emitter__, f"Ajout rapide · {text}")
        cal = calendar_id or self.valves.DEFAULT_CALENDAR_ID

        try:
            event = await self._api(
                "POST",
                f"/calendars/{cal}/events/quickAdd",
                __event_emitter__,
                params={"text": text},
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur lors de l'ajout rapide : {exc}"

        await self._emit(__event_emitter__, "Événement créé", done=True)
        return "Evenement cree :\n\n" + self._fmt_event(event)

    async def update_event(
        self,
        event_id: str,
        summary: str = "",
        start_datetime: str = "",
        end_datetime: str = "",
        description: str = "",
        location: str = "",
        attendees: str = "",
        send_updates: str = "none",
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Modifie un événement existant dans Google Calendar.
        Seuls les champs fournis sont modifiés — les autres restent
        inchangés. À utiliser quand l'utilisateur dit : "déplace mon
        rendez-vous à 16h", "change le lieu de la réunion", "ajoute
        Bob à l'invitation".

        Si l'utilisateur ne connaît pas l'event_id, utiliser d'abord
        search_events() pour le retrouver, puis modifier.

        :param event_id: ID de l'événement à modifier (obligatoire).
        :param summary: Nouveau titre.
        :param start_datetime: Nouvelle date/heure de début ISO 8601.
        :param end_datetime: Nouvelle date/heure de fin ISO 8601.
        :param description: Nouvelle description.
        :param location: Nouveau lieu.
        :param attendees: Nouveaux invités (remplace la liste existante).
        :param send_updates: "all" pour notifier, "none" sinon.
        :param calendar_id: ID du calendrier (vide = par défaut).
        :return: Confirmation avec les détails mis à jour.
        """
        await self._emit(__event_emitter__, "Modification")
        cal = calendar_id or self.valves.DEFAULT_CALENDAR_ID
        tz = self.valves.DEFAULT_TIMEZONE

        # Récupérer l'événement existant pour merger (PATCH partiel)
        try:
            existing = await self._api(
                "GET", f"/calendars/{cal}/events/{event_id}", __event_emitter__
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Événement introuvable : {exc}"

        if summary:
            existing["summary"] = summary
        if description:
            existing["description"] = description
        if location:
            existing["location"] = location
        if start_datetime:
            existing["start"] = {"dateTime": start_datetime, "timeZone": tz}
        if end_datetime:
            existing["end"] = {"dateTime": end_datetime, "timeZone": tz}
        if attendees:
            existing["attendees"] = [
                {"email": e.strip()} for e in attendees.split(",") if e.strip()
            ]

        try:
            event = await self._api(
                "PUT",
                f"/calendars/{cal}/events/{event_id}",
                __event_emitter__,
                json_body=existing,
                params={"sendUpdates": send_updates},
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur lors de la modification : {exc}"

        await self._emit(__event_emitter__, "Événement modifié", done=True)
        return "Evenement mis a jour :\n\n" + self._fmt_event(event)

    async def delete_event(
        self,
        event_id: str,
        send_updates: str = "none",
        calendar_id: str = "",
        __event_emitter__=None,
    ) -> str:
        """
        Supprime un événement de Google Calendar.
        À utiliser quand l'utilisateur dit : "supprime mon rendez-vous",
        "annule la réunion de lundi", "enlève cet événement".

        Si l'utilisateur ne connaît pas l'event_id, utiliser d'abord
        search_events() pour retrouver l'événement.

        :param event_id: ID de l'événement à supprimer (obligatoire).
        :param send_updates: "all" pour notifier les invités, "none" sinon.
        :param calendar_id: ID du calendrier (vide = par défaut).
        :return: Confirmation de suppression.
        """
        await self._emit(__event_emitter__, "Suppression")
        cal = calendar_id or self.valves.DEFAULT_CALENDAR_ID

        try:
            await self._api(
                "DELETE",
                f"/calendars/{cal}/events/{event_id}",
                __event_emitter__,
                params={"sendUpdates": send_updates},
            )
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur lors de la suppression : {exc}"

        await self._emit(__event_emitter__, "Événement supprimé", done=True)
        return f"Evenement `{event_id}` supprime avec succes."

    async def list_calendars(
        self,
        __event_emitter__=None,
    ) -> str:
        """
        Liste tous les calendriers Google accessibles (principal,
        partagés, jours fériés, etc.). À utiliser quand l'utilisateur
        demande "quels agendas j'ai ?", ou pour trouver l'ID d'un
        calendrier spécifique avant de le cibler.

        :return: Liste des calendriers avec leur ID et rôle d'accès.
        """
        await self._emit(__event_emitter__, "Récupération des agendas")

        try:
            data = await self._api("GET", "/users/me/calendarList", __event_emitter__)
        except RuntimeError as exc:
            await self._emit(__event_emitter__, str(exc), done=True)
            return f"Erreur : {exc}"

        cals = data.get("items", [])
        if not cals:
            return "Aucun calendrier trouvé."

        lines = []
        for c in cals:
            primary = " (principal)" if c.get("primary") else ""
            name = c.get("summary") or "(sans nom)"
            role = c.get("accessRole", "?")
            tz = c.get("timeZone", "?")
            lines.append(
                f"**{name}**{primary}\n"
                f"   ID     : `{c['id']}`\n"
                f"   Acces  : {role} · Timezone : {tz}"
            )

        await self._emit(
            __event_emitter__, f"{_plural(len(cals), 'agenda')}", done=True
        )
        return "\n\n".join(lines)

    async def check_auth_status(
        self,
        __event_emitter__=None,
    ) -> str:
        """
        Vérifie que les credentials Google sont valides et que l'API
        Calendar est accessible. À utiliser quand l'utilisateur se
        plaint que le calendrier ne répond pas, ou pour confirmer que
        tout est bien configuré.

        :return: Message d'état avec le compte connecté.
        """
        await self._emit(__event_emitter__, "Vérification des identifiants")

        try:
            token = await self._get_access_token()
        except RuntimeError as exc:
            msg = f"Erreur d'authentification : {exc}"
            await self._emit(__event_emitter__, msg, done=True)
            return msg

        try:
            cal = await self._api("GET", "/calendars/primary", __event_emitter__)
        except RuntimeError as exc:
            msg = f"Token obtenu mais API inaccessible : {exc}"
            await self._emit(__event_emitter__, msg, done=True)
            return msg

        email = cal.get("summary") or cal.get("id") or "inconnu"
        tz = cal.get("timeZone", "?")
        msg = (
            f"Google Calendar connecte.\n"
            f"   Compte   : {email}\n"
            f"   Timezone calendrier : {tz}\n"
            f"   Timezone Tool       : {self.valves.DEFAULT_TIMEZONE}"
        )
        await self._emit(__event_emitter__, "Connexion vérifiée", done=True)
        return msg
