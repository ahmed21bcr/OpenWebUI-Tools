"""
title: OpenRouter ZDR Filter
description: Injecte provider.zdr=true dans chaque requête OpenRouter depuis OWUI.
version: 1.0.1
licence: Attribution-NonCommercial
licence_file: LICENSE
copyright: Copyright (c) 2026 Anas and Ahmed
"""

from pydantic import BaseModel, Field


class Filter:

    class Valves(BaseModel):
        ZDR_ENABLED: bool = Field(
            default=True,
            description="Activer Zero Data Retention sur toutes les requêtes.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def inlet(self, body: dict, __user__=None) -> dict:
        if not self.valves.ZDR_ENABLED:
            return body

        # Injecter provider.zdr comme objet JSON dans le body
        if "provider" not in body:
            body["provider"] = {}

        body["provider"]["zdr"] = True

        return body
