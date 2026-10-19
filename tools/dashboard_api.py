"""Production entry point for the Nuestra Casita Dashboard API."""

import uvicorn

from casita.api import create_dashboard_api, load_dashboard_api_configuration
from casita.bootstrap import build_grocy_application, load_configuration


api_configuration = load_dashboard_api_configuration()
application_configuration = load_configuration()
application = build_grocy_application(
    configuration=application_configuration,
    timezone_name=application_configuration.timezone,
)
app = create_dashboard_api(application, api_configuration)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=api_configuration.host,
        port=api_configuration.port,
        log_level=api_configuration.log_level,
        access_log=False,
    )
