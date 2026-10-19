"""Tests for shopping-list CLI presentation."""

from contextlib import redirect_stdout
from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from unittest import TestCase

from casita.application import ServiceResult
from casita.domain import ShoppingItem, ShoppingList


CLI_PATH = Path(__file__).resolve().parents[1] / "tools" / "casita.py"
CLI_SPEC = spec_from_file_location("casita_cli", CLI_PATH)

if CLI_SPEC is None or CLI_SPEC.loader is None:
    raise RuntimeError("Unable to load the Nuestra Casita CLI.")

CLI = module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(CLI)


class ShoppingListCliTests(TestCase):
    def test_parser_exposes_shopping_lists_command(self):
        args = CLI.build_parser(("all",)).parse_args(["shopping-lists"])

        self.assertEqual(args.command, "shopping-lists")

    def test_renders_multiple_and_empty_lists(self):
        result = ServiceResult(
            records=(
                ShoppingList(
                    id="one",
                    household_id="household",
                    name="Groceries",
                    items=(
                        ShoppingItem(
                            id="item-one",
                            name="Milk",
                            quantity=Decimal("2.50"),
                            unit="bottles",
                            note="Organic",
                        ),
                        ShoppingItem(
                            id="item-two",
                            name="Bread",
                            quantity=Decimal("1"),
                            unit="loaf",
                            checked=True,
                        ),
                    ),
                ),
                ShoppingList(
                    id="two",
                    household_id="household",
                    name="Hardware",
                ),
            ),
            refreshed_at=None,
        )
        output = StringIO()

        with redirect_stdout(output):
            CLI._print_shopping_lists(result)

        self.assertEqual(
            output.getvalue(),
            "Groceries\n"
            "[ ] Milk: 2.50 bottles — Organic\n"
            "[x] Bread: 1 loaf\n"
            "\n"
            "Hardware\n"
            "(empty)\n",
        )
