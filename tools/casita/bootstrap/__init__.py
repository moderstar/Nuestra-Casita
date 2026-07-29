"""Composition root for constructing Nuestra Casita."""

from casita.bootstrap.application import (
    ApplicationServices,
    NuestraCasitaApplication,
    build_application,
)
from casita.bootstrap.grocy import build_grocy_application

__all__ = [
    "ApplicationServices",
    "NuestraCasitaApplication",
    "build_application",
    "build_grocy_application",
]
