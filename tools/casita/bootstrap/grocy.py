"""Construct Nuestra Casita with the production Grocy read adapter."""

from casita.bootstrap.application import (
    NuestraCasitaApplication,
    build_application,
)
from casita.dashboard import (
    DEFAULT_DASHBOARD_CONTRACT,
    DashboardContract,
)
from casita.integrations import Capability
from casita.integrations.grocy import GrocyReadAdapter


def build_grocy_application(
    *,
    base_url: str,
    api_key: str,
    timezone_name: str = "UTC",
    dashboard_contract: DashboardContract = DEFAULT_DASHBOARD_CONTRACT,
) -> NuestraCasitaApplication:
    """Build an application whose household data is owned by Grocy."""

    grocy = GrocyReadAdapter.from_credentials(
        base_url,
        api_key,
        timezone_name=timezone_name,
    )
    capabilities = (
        Capability.SHOPPING,
        Capability.INVENTORY,
        Capability.RECIPES,
        Capability.CHORES,
    )

    return build_application(
        integrations=(grocy,),
        capability_owners={
            capability: (grocy.descriptor.key,)
            for capability in capabilities
        },
        dashboard_contract=dashboard_contract,
    )
