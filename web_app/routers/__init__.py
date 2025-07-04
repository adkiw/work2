from fastapi import APIRouter

from .kroviniai import router as kroviniai_router
from .planavimas import router as planavimas_router
from .trailer_swap import router as trailer_swap_router
from .priekabos import router as priekabos_router
from .vairuotojai import router as vairuotojai_router
from .darbuotojai import router as darbuotojai_router
from .grupes import router as grupes_router
from .group_regions import router as group_regions_router
from .klientai import router as klientai_router
from .trailer_types import router as trailer_types_router
from .trailer_specs import router as trailer_specs_router
from .settings import router as settings_router
from .registracijos import router as registracijos_router
from .audit import router as audit_router
from .updates import router as updates_router
from .health import router as health_router
from .constants import router as constants_router

router = APIRouter()
for r in [
    kroviniai_router,
    planavimas_router,
    trailer_swap_router,
    priekabos_router,
    vairuotojai_router,
    darbuotojai_router,
    grupes_router,
    group_regions_router,
    klientai_router,
    trailer_types_router,
    trailer_specs_router,
    settings_router,
    registracijos_router,
    audit_router,
    updates_router,
    health_router,
    constants_router,
]:
    router.include_router(r)
