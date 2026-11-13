#!/usr/bin/env python3
"""Place Unzipping the Dawn.

This program does not draw. It checks the JPEG that ships beside it and
copies those exact bytes to the grader's output file. The picture is a
surreal ukiyo-e print: villagers on a ridge haul a brass zipper open across
the night, and dawn spills through the gap.
"""

import os
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "art" / "unzipping-the-dawn.jpg"
OUT_NAME = "entry.png"
BYTE_CAP = 1048576
EDGE_CAP = 1024
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


def read_source():
    if not SOURCE.is_file():
        raise SystemExit(f"missing artwork: {SOURCE}")
    return SOURCE.read_bytes()


def require_ends(blob):
    if len(blob) < 4 or blob[:2] != JPEG_SOI:
        raise SystemExit("artwork is not a JPEG: SOI marker is absent")
    if blob[-2:] != JPEG_EOI:
        raise SystemExit("artwork is not a JPEG: EOI marker is absent")


def frame_edges(blob):
    """Return width, height from the first SOF0 or SOF2 segment."""
    cursor = 2
    total = len(blob)
    while cursor < total - 1:
        if blob[cursor] != 0xFF:
            raise SystemExit("artwork JPEG has a broken marker")
        while cursor < total and blob[cursor] == 0xFF:
            cursor += 1
        if cursor >= total:
            break
        kind = blob[cursor]
        cursor += 1
        if kind == 0xD9:
            break
        if kind in (0xD8, 0x01) or 0xD0 <= kind <= 0xD7:
            continue
        if cursor + 2 > total:
            raise SystemExit("artwork JPEG segment is truncated")
        seg_len = struct.unpack(">H", blob[cursor:cursor + 2])[0]
        if seg_len < 2 or cursor + seg_len > total:
            raise SystemExit("artwork JPEG segment length is invalid")
        if kind in (0xC0, 0xC2):
            if seg_len < 7:
                raise SystemExit("artwork JPEG frame header is short")
            height, width = struct.unpack(">HH", blob[cursor + 3:cursor + 7])
            return width, height
        if kind == 0xDA:
            cursor += seg_len
            while cursor < total - 1:
                if blob[cursor] != 0xFF:
                    cursor += 1
                    continue
                nxt = blob[cursor + 1]
                if nxt == 0x00:
                    cursor += 2
                    continue
                if nxt == 0xFF:
                    cursor += 1
                    continue
                break
            continue
        cursor += seg_len
    raise SystemExit("artwork JPEG has no SOF0 or SOF2 frame")


def vet_artwork(blob):
    if len(blob) > BYTE_CAP:
        raise SystemExit(f"artwork is {len(blob)} bytes, over the {BYTE_CAP} cap")
    require_ends(blob)
    width, height = frame_edges(blob)
    if width < 1 or height < 1 or width > EDGE_CAP or height > EDGE_CAP:
        raise SystemExit(f"artwork is {width}x{height}, over the {EDGE_CAP}px cap")
    return width, height


def main():
    blob = read_source()
    width, height = vet_artwork(blob)
    folder = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / OUT_NAME
    staging = folder / (OUT_NAME + ".partial")
    staging.write_bytes(blob)
    os.replace(staging, dest)
    print(f"placed {width}x{height} JPEG, {len(blob)} bytes, at {dest}")


if __name__ == "__main__":
    main()
