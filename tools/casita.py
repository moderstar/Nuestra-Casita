import argparse

from casita.exporter import export_products
from casita.lookups import build_lookups
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

    args = parser.parse_args()

    if args.command == "lookups":
        print(build_lookups())

    elif args.command == "validate":
        validate()

    elif args.command == "import":
        if args.import_command == "products":
            print("Product importer will be connected here.")

    elif args.command == "export":
        if args.export_command == "products":
            export_products()


if __name__ == "__main__":
    main()
