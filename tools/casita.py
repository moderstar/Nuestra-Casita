#!/usr/bin/env python3

import argparse

from casita.lookups import show as show_lookups
from casita.validator import validate

def main():
    parser = argparse.ArgumentParser(
        prog="casita",
        description="Nuestra Casita Management CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "lookups",
        help="Display Grocy lookup tables",
    )

    subparsers.add_parser(
        "validate",
        help="Validate catalog CSV files",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import data into Grocy",
    )

    import_parser.add_argument(
        "target",
        choices=["products"],
    )

    args = parser.parse_args()

    if args.command == "lookups":
        show_lookups()

    elif args.command == "validate":
        validate()

    elif args.command == "import":
        if args.target == "products":
            print("Product import will go here.")


if __name__ == "__main__":
    main()
