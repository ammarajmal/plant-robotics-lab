"""Developer-facing command line entry point."""

import argparse
from dataclasses import replace
from pathlib import Path

from plant_robotics.playback import ConfigError, PlaybackError, load_config, render_three_view


def main() -> None:
    parser = argparse.ArgumentParser(prog="prl", description="Plant Robotics Lab CLI")
    parser.add_argument("command", choices=["status", "playback"])
    parser.add_argument("mode", nargs="?", choices=["three-view"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.command == "status":
        print("PRL foundation and deterministic video ingestion are installed")
        return
    if args.mode != "three-view" or args.config is None:
        parser.error("playback requires: prl playback three-view --config PATH")
    try:
        config = load_config(args.config)
        if args.output_dir is not None:
            config = replace(config, output_dir=args.output_dir)
        render_three_view(config)
    except (ConfigError, FileNotFoundError, PlaybackError) as exc:
        parser.exit(2, f"prl: error: {exc}\n")
    print(f"playback complete: {config.resolved_output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
