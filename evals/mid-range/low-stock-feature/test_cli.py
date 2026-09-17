import io
import unittest
from contextlib import redirect_stdout

from cli import main


class CliTests(unittest.TestCase):
    def run_cli(self, *argv: str) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            main(list(argv))
        return output.getvalue()

    def test_default_output_is_preserved(self) -> None:
        self.assertEqual(self.run_cli(), "Inventory: 3 items\n")

    def test_low_stock_lists_matching_items_alphabetically(self) -> None:
        self.assertEqual(self.run_cli("--low-stock", "4"), "adapter,wire\n")

    def test_low_stock_can_have_no_matches(self) -> None:
        self.assertEqual(self.run_cli("--low-stock", "1"), "\n")


if __name__ == "__main__":
    unittest.main()
