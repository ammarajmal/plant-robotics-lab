"""Developer-facing command line entry point."""

import argparse
from dataclasses import replace
from pathlib import Path

from plant_robotics.doctor import report, run_checks
from plant_robotics.domain.datasets import ManifestError, SourceManifest
from plant_robotics.io.decode_audit import SourceDriftError, audit_episode
from plant_robotics.io.hashing import sha256_file
from plant_robotics.io.resolver import (
    SourceResolutionError,
    check_destination,
    load_catalog,
    load_manifest,
    publish_json,
    resolve_data_root,
    resolve_episode,
    verify_episode,
    write_manifest,
)
from plant_robotics.io.video import VideoIngestionError
from plant_robotics.playback import ConfigError, PlaybackError, load_config, render_three_view


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prl", description="Plant Robotics Lab CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("status", help="print installation status")
    commands.add_parser("doctor", help="read-only environment readiness check")

    playback = commands.add_parser("playback", help="render headless playback evidence")
    playback.add_argument("mode", nargs="?", choices=["three-view"])
    playback.add_argument("--config", type=Path)
    playback.add_argument("--output-dir", type=Path)
    playback.add_argument("--data-root", type=Path, help="for configs using source_manifest")

    data = commands.add_parser("data", help="read-only dataset source manifests")
    data_commands = data.add_subparsers(dest="data_command", required=True)

    resolve = data_commands.add_parser("resolve", help="write a manifest for one episode")
    resolve.add_argument("--catalog", type=Path, required=True)
    resolve.add_argument("--task-id", required=True)
    resolve.add_argument("--episode-id", required=True)
    resolve.add_argument("--output", type=Path, required=True)
    resolve.add_argument("--data-root", type=Path, help="defaults to the catalog's env variable")
    resolve.add_argument("--no-hash", action="store_true", help="skip SHA-256 (marks unverified)")
    resolve.add_argument("--force", action="store_true", help="replace an existing output file")

    verify = data_commands.add_parser("verify", help="compare a manifest with current files")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--data-root", type=Path, help="defaults to the manifest's env variable")
    verify.add_argument("--catalog", type=Path, help="also bind the manifest to its catalog")
    verify.add_argument("--no-hash", action="store_true", help="skip SHA-256 comparison")

    audit = data_commands.add_parser("audit", help="decode every frame and write an audit JSON")
    audit.add_argument("--manifest", type=Path, required=True)
    audit.add_argument("--catalog", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    audit.add_argument("--data-root", type=Path, help="defaults to the manifest's env variable")
    audit.add_argument("--force", action="store_true", help="replace an existing output file")
    return parser


def _playback(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.mode != "three-view" or args.config is None:
        parser.error("playback requires: prl playback three-view --config PATH")
    try:
        config = load_config(args.config, data_root=args.data_root)
        if args.output_dir is not None:
            config = replace(config, output_dir=args.output_dir)
        render_three_view(config)
    except (ConfigError, FileNotFoundError, PlaybackError) as exc:
        parser.exit(2, f"prl: error: {exc}\n")
    print(f"playback complete: {config.resolved_output_dir / 'manifest.json'}")


def _audit(args: argparse.Namespace, manifest: SourceManifest, root: Path) -> None:
    catalog = load_catalog(args.catalog)
    check_destination(args.output, root, force=args.force)
    try:
        audit = audit_episode(manifest, root, catalog, manifest_sha256=sha256_file(args.manifest))
    except SourceDriftError as exc:
        print("sources differ from the manifest; nothing decoded:")
        for difference in exc.differences:
            print(f"  {difference}")
        raise SystemExit(1) from exc
    publish_json(audit, args.output, data_root=root, force=args.force)
    summary = audit["summary"]
    print(f"audit written: {args.output} [episode digest {summary['episode_digest'][:16]}]")
    for stream in audit["streams"]:
        print(
            f"  {stream['camera_id']}: {stream['status']}, decoded "
            f"{stream.get('decoded_frame_count')} frames"
        )
    if not summary["all_streams_complete"]:
        print("INTEGRITY FINDING: at least one stream did not decode completely")
        raise SystemExit(1)


def _data(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    try:
        if args.data_command == "resolve":
            catalog = load_catalog(args.catalog)
            root = resolve_data_root(args.data_root, catalog.root_variable)
            check_destination(args.output, root, force=args.force)
            manifest = resolve_episode(
                catalog, root, args.task_id, args.episode_id, compute_hash=not args.no_hash
            )
            write_manifest(manifest, args.output, data_root=root, force=args.force)
            hashed = "unverified (no hashes)" if args.no_hash else "SHA-256 recorded"
            print(f"manifest written: {args.output} [{hashed}]")
            return
        manifest = load_manifest(args.manifest)
        root = resolve_data_root(args.data_root, manifest.root_variable)
        if args.data_command == "audit":
            _audit(args, manifest, root)
            return
        catalog = load_catalog(args.catalog) if args.catalog else None
        result = verify_episode(manifest, root, compute_hash=not args.no_hash, catalog=catalog)
    except (ManifestError, SourceResolutionError, VideoIngestionError, OSError) as exc:
        parser.exit(2, f"prl: error: {exc}\n")
    if not result.ok:
        print("manifest differs from current files:")
        for difference in result.differences:
            print(f"  {difference}")
        parser.exit(1)
    scope = (
        "sizes, hashes, metadata"
        if result.hashes_checked
        else "sizes, metadata (hashes NOT checked)"
    )
    print(f"manifest matches current files: {scope}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        print("PRL foundation and deterministic video ingestion are installed")
    elif args.command == "doctor":
        if not report(run_checks()):
            raise SystemExit(1)
    elif args.command == "playback":
        _playback(parser, args)
    else:
        _data(parser, args)


if __name__ == "__main__":
    main()
