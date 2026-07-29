"""Composition root for constructing Nuestra Casita."""

from casita.bootstrap.application import (
    ApplicationServices,
    NuestraCasitaApplication,
    build_application,
)
from casita.bootstrap.grocy import build_grocy_application
from casita.bootstrap.configuration import (
    ApplicationConfiguration,
    load_configuration,
)

__all__ = [
    "ApplicationServices",
    "ApplicationConfiguration",
    "NuestraCasitaApplication",
    "build_application",
    "build_grocy_application",
    "load_configuration",
]
