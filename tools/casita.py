import argparse

from casita.exporter import export_products
from casita.lookups import show
from casita.sync import sync_products
from casita.validator import validate


def main():
    parser = argparse.ArgumentParser(
        description="Nuestra Casita management tool"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    subparsers.add_parser(
        "lookups",
        help="Display Grocy lookup tables"
    )

    subparsers.add_parser(
        "validate",
        help="Validate catalog files"
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import data into Grocy"
    )

    import_subparsers = import_parser.add_subparsers(
        dest="import_command",
        required=True
    )

    import_subparsers.add_parser(
        "products",
        help="Import products into Grocy"
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Export data from Grocy"
    )

    export_subparsers = export_parser.add_subparsers(
        dest="export_command",
        required=True
    )

    export_subparsers.add_parser(
        "products",
        help="Export products to catalog/products.csv"
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Synchronize catalog with Grocy"
    )

    sync_subparsers = sync_parser.add_subparsers(
        dest="sync_command",
        required=True
    )

    sync_products_parser = sync_subparsers.add_parser(
        "products",
        help="Synchronize products with Grocy"
    )

    sync_products_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to Grocy"
    )

    args = parser.parse_args()

    if args.command == "lookups":
        show()

    elif args.command == "validate":
        validate()

    elif args.command == "import":
        if args.import_command == "products":
            print("Product importer will be connected here.")

    elif args.command == "export":
        if args.export_command == "products":
            export_products()

    elif args.command == "sync":
        if args.sync_command == "products":
            sync_products(apply=args.apply)


if __name__ == "__main__":
    main()
