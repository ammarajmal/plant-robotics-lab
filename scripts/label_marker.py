#!/usr/bin/env python3
"""Interactive ground-truth labeller for one video (needs a display).

Keys: click = mark marker centre (visibility 2); 'p' then click = partial (1);
'o' = occluded (0); 'a'/'d' = back/forward 1 frame; 'w'/'s' = +/-10 frames;
'q' = save and quit. Output matches the left_arm label CSV format. Refuses to
overwrite an existing file.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    args = ap.parse_args()
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    cap = cv2.VideoCapture(str(args.video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end = min(args.end if args.end is not None else total - 1, total - 1)
    labels: dict[int, tuple[str, str, int]] = {}
    state = {"frame": args.start, "partial": False}

    def on_mouse(event: int, x: int, y: int, *_: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            vis = 1 if state["partial"] else 2
            labels[state["frame"]] = (f"{x}", f"{y}", vis)
            state["partial"] = False

    cv2.namedWindow("label")
    cv2.setMouseCallback("label", on_mouse)
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, state["frame"])
        ok, image = cap.read()
        if not ok:
            break
        if state["frame"] in labels:
            x, y, vis = labels[state["frame"]]
            cv2.circle(image, (int(x), int(y)), 8, (0, 255, 0) if vis == 2 else (0, 165, 255), 2)
        text = f"frame {state['frame']}/{end} labelled={len(labels)}"
        cv2.putText(image, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("label", image)
        key = cv2.waitKey(30) & 0xFF
        step = {ord("d"): 1, ord("a"): -1, ord("w"): 10, ord("s"): -10}.get(key, 0)
        if key == ord("p"):
            state["partial"] = True
        elif key == ord("o"):
            labels[state["frame"]] = ("", "", 0)
        elif key == ord("q"):
            break
        state["frame"] = max(args.start, min(end, state["frame"] + step))
    with args.output.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame", "x", "y", "w", "h", "visibility", "notes"])
        for frame in sorted(labels):
            x, y, vis = labels[frame]
            writer.writerow([frame, x, y, "", "", vis, ""])
    print(f"saved {len(labels)} labels to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
