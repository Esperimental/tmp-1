import unittest

from formatters import inventory_label
from inventory import available_quantity


class InventoryTests(unittest.TestCase):
    def test_reserved_stock_is_not_available(self) -> None:
        self.assertEqual(available_quantity(12, 5), 7)

    def test_all_stock_can_be_reserved(self) -> None:
        self.assertEqual(available_quantity(4, 4), 0)

    def test_formatting_is_unrelated_to_availability(self) -> None:
        self.assertEqual(inventory_label(7), "Available: 7")


if __name__ == "__main__":
    unittest.main()
