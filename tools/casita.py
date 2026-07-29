"""Unified command-line interface for Nuestra Casita."""

import argparse
from datetime import timezone

from casita.bootstrap import (
    build_grocy_application,
    load_configuration,
)
from casita.domain import Household
from casita.integrations import SyncAction
from casita.registry import SYNC_ALL_COMMAND


def build_parser(sync_resources):
    """Build the presentation-only argparse command tree."""

    parser = argparse.ArgumentParser(
        prog="casita",
        description="Nuestra Casita household operating system",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("dashboard", help="Show household status")
    subparsers.add_parser("doctor", help="Diagnose configuration and services")
    subparsers.add_parser("inventory", help="Show normalized inventory")
    subparsers.add_parser("recipes", help="Show normalized recipes")

    sync_parser = subparsers.add_parser(
        "sync",
        help="Synchronize declarative resources",
    )
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command")

    for resource_name in sync_resources:
        resource_parser = sync_subparsers.add_parser(resource_name)
        resource_parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the synchronization plan",
        )

    sync_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply all synchronization plans",
    )

    subparsers.add_parser("lookups", help="Display Grocy lookup tables")
    subparsers.add_parser("validate", help="Validate catalog files")
    export_parser = subparsers.add_parser("export", help="Export Grocy data")
    export_subparsers = export_parser.add_subparsers(
        dest="export_command",
        required=True,
    )
    export_subparsers.add_parser("products")
    import_parser = subparsers.add_parser("import", help="Import Grocy data")
    import_subparsers = import_parser.add_subparsers(
        dest="import_command",
        required=True,
    )
    import_subparsers.add_parser("products")
    return parser


def main():
    """Construct the application and route commands to application services."""

    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument("command", nargs="?")
    known, _ = preliminary.parse_known_args()
    configuration = load_configuration(
        strict=known.command not in ("doctor", None),
    )
    application = build_grocy_application(
        configuration=configuration,
        timezone_name=configuration.timezone,
    )
    sync_service = application.sync

    if sync_service is None:
        raise RuntimeError("Synchronization service is not configured.")

    args = build_parser(sync_service.resources).parse_args()
    household = Household(
        id=configuration.household_id,
        name=configuration.household_name,
        timezone=configuration.timezone,
    )

    if args.command == "dashboard":
        _print_dashboard(
            application.dashboard.overview(
                household,
                configuration_valid=configuration.exists,
            )
        )
    elif args.command == "doctor":
        if application.doctor is None:
            raise RuntimeError("Doctor service is not configured.")

        report = application.doctor.run()
        _print_doctor(report)
        raise SystemExit(0 if report.passed else 1)
    elif args.command == "inventory":
        _print_inventory(application.services.inventory.read(household.id))
    elif args.command == "recipes":
        _print_recipes(application.services.recipes.read(household.id))
    elif args.command == "sync":
        sync_service.synchronize(
            household.id,
            args.sync_command or SYNC_ALL_COMMAND,
            apply=args.apply,
            on_resource=_print_sync_resource_header,
            on_plan=lambda plan: _print_sync_plan(
                plan,
                dry_run=not args.apply,
            ),
            on_result=_print_sync_result if args.apply else None,
        )
    elif args.command == "lookups":
        _require_maintenance(application).lookups()
    elif args.command == "validate":
        _require_maintenance(application).validate()
    elif args.command == "export":
        _require_maintenance(application).export(args.export_command)
    elif args.command == "import":
        print("Product importer will be connected here.")


def _print_dashboard(dashboard):
    print("Nuestra Casita")
    print("=" * 40)

    for integration in dashboard.integrations:
        print()
        print(integration.display_name)
        print(f"- {'Connected' if integration.connected else 'Unavailable'}")
        print(f"- Version: {integration.version or 'Unknown'}")
        print(f"- Database: {integration.database or 'Unknown'}")
        metrics = dict(integration.metrics)
        print()
        print("Inventory")
        print(f"- Product count: {metrics.get('products', 0)}")
        print(f"- Recipe count: {metrics.get('recipes', 0)}")
        print(f"- Location count: {metrics.get('locations', 0)}")

    print()
    print("Health")
    print(
        "- Configuration: "
        f"{'PASS' if dashboard.configuration_valid else 'FAIL'}"
    )
    print(
        "- Last synchronization: "
        + (
            dashboard.last_synchronization.astimezone(timezone.utc).isoformat()
            if dashboard.last_synchronization
            else "Not recorded"
        )
    )
    print(
        "- Missing resources: "
        + (", ".join(dashboard.missing_resources) or "None")
    )
    print("- Errors: " + ("; ".join(dashboard.errors) or "None"))


def _print_doctor(report):
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}")

        if check.message:
            print(f"     {check.message}")


def _print_inventory(result):
    for inventory in result.records:
        for item in inventory.items:
            print(f"{item.name}: {item.quantity} {item.unit}".rstrip())

    for failure in result.failures:
        print(f"ERROR {failure.message}")


def _print_recipes(result):
    for recipe in result.records:
        print(recipe.name)

    for failure in result.failures:
        print(f"ERROR {failure.message}")


def _print_sync_resource_header(resource_name):
    print()
    print("#" * 40)
    print(f"Synchronizing {resource_name.replace('-', ' ').title()}")
    print("#" * 40)
    print()


def _print_sync_dry_run(resource_name):
    print()
    print("=" * 40)
    print("Dry Run")
    print("=" * 40)
    print()
    print("No changes were made.")
    print()
    print("Run again with:")
    print()
    print(f"    python tools/casita.py sync {resource_name} --apply")


def _print_sync_plan(plan, *, dry_run):
    print("Loading catalog...")
    print(f"Catalog {plan.resource_label}: {plan.catalog_count}")
    print()
    print("Loading Grocy...")
    print(f"Grocy {plan.resource_label}: {plan.backend_count}")
    print()

    if plan.lookups_loaded:
        print("Loading lookup tables...")
        print("Lookup tables loaded.")
        print()

    print("Execution Plan")
    print("=" * 40)
    print()

    for change in plan.changes:
        if change.action == SyncAction.UPDATE:
            print(f"~ UPDATE    {change.display_name}")

            for difference in change.differences:
                print(f"    {difference.label}")
                print(f"      Grocy:   {difference.current_display}")
                print(f"      Catalog: {difference.desired_display}")

            print()

    creates = tuple(
        change
        for change in plan.changes
        if change.action == SyncAction.CREATE
    )

    for change in creates:
        print(f"+ CREATE    {change.display_name}")

    if creates:
        print()

    print("=" * 40)
    print("Summary")
    print("=" * 40)
    print(
        "Match : "
        f"{sum(change.action == SyncAction.MATCH for change in plan.changes)}"
    )
    print(
        "Update: "
        f"{sum(change.action == SyncAction.UPDATE for change in plan.changes)}"
    )
    print(f"Create: {len(creates)}")

    if dry_run:
        _print_sync_dry_run(plan.resource)


def _print_sync_result(result):
    print()
    print("=" * 40)
    print(f"Applying {result.resource_label.title()} Plan")
    print("=" * 40)
    print()
    print(f"{result.created} {result.resource_label} to create")
    print(f"{result.updated} {result.resource_label} to update")
    print()

    if result.lookups_loaded:
        print("Loading lookup tables...")
        print("Lookup tables loaded.")
        print()

    for change in result.changes:
        operation = change.action.value
        symbol = "+" if change.action == SyncAction.CREATE else "~"
        print(f"{symbol} {operation.upper():9} {change.display_name}")
        print(f"    {operation.capitalize()}d successfully.")
        print()

    if result.created or result.updated:
        print("=" * 40)
        print("Apply Summary")
        print("=" * 40)
        print()
        print(f"Matched: {result.matched}")
        print(f"Created: {result.created}")
        print(f"Updated: {result.updated}")


def _require_maintenance(application):
    if application.maintenance is None:
        raise RuntimeError("Maintenance service is not configured.")

    return application.maintenance


if __name__ == "__main__":
    main()
