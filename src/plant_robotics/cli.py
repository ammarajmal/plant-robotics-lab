"""Developer-facing command line entry point."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="prl", description="Plant Robotics Lab CLI")
    parser.add_argument("command", choices=["status"])
    args = parser.parse_args()
    if args.command == "status":
        print("PRL foundation installed; robotics modules are not yet implemented")


if __name__ == "__main__":
    main()
