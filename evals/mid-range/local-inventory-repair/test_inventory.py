import unittest

from inventory import add_stock, can_fulfil


class InventoryTests(unittest.TestCase):
    def test_add_stock_accumulates_inventory(self) -> None:
        self.assertEqual(add_stock(7, 5), 12)

    def test_can_fulfil_accepts_available_positive_request(self) -> None:
        self.assertTrue(can_fulfil(10, 4))

    def test_can_fulfil_rejects_excessive_request(self) -> None:
        self.assertFalse(can_fulfil(3, 4))

    def test_can_fulfil_rejects_zero_and_negative_requests(self) -> None:
        self.assertFalse(can_fulfil(10, 0))
        self.assertFalse(can_fulfil(10, -2))


if __name__ == "__main__":
    unittest.main()
