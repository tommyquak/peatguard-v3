"""PeatGuard operator + villager REST API.

Backs the Next.js operator dashboard (apps/web) and the Expo villager mobile
app (apps/mobile). The five-state task lifecycle
(available -> accepted -> submitted -> approved | revision -> paid) is the
single contract shared across all three surfaces.
"""

from peatguard.api.router import api_router

__all__ = ["api_router"]
