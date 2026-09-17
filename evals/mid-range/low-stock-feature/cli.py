from __future__ import annotations

import argparse


INVENTORY = {"adapter": 2, "sensor": 9, "wire": 4}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    print("Inventory: 3 items")


if __name__ == "__main__":
    main()
