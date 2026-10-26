"""Draw the 24x24 icons the Grasshopper components need.

The componentizer requires an ``icon.png`` beside every ``code.py``, and a
checked-in binary is something nobody can review or edit. So each icon is
written here as a 12x12 text sketch, doubled to the 24x24 the toolbar wants,
and encoded with the standard library -- no image library, and no reason for
the generated file to drift from what the source says it should be.

Legend, per cell:

===== ==========================================================
``#``  the object: dark ink
``+``  a secondary element: mid grey
``.``  transparent
===== ==========================================================

Run ``python scripts/make_icons.py`` after editing a sketch, and commit both
the sketch and the regenerated png.
"""

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
COMPONENTS = os.path.join(HERE, os.pardir, "src", "compas_vol", "ghpython", "components")

SCALE = 2
SIZE = 12

#: RGBA per legend character. The ink is COMPAS's dark grey rather than pure
#: black, so the icons sit with the rest of the ecosystem's toolbars.
INK = (49, 49, 49, 255)
MID = (140, 140, 140, 255)
CLEAR = (0, 0, 0, 0)
PALETTE = {"#": INK, "+": MID, ".": CLEAR}

#: One 12x12 sketch per component folder. Edit these, not the png.
ICONS = {
    # An "i" in a ring: the diagnostics component.
    "Cv_Info": [
        "....++++....",
        "..++....++..",
        ".+........+.",
        "+...####...+",
        "+..........+",
        "+...####...+",
        "+.....##...+",
        "+.....##...+",
        ".+..######.+",
        ".+........+.",
        "..++....++..",
        "....++++....",
    ],
    "Cv_Sphere": [
        "....####....",
        "..########..",
        ".##########.",
        "############",
        "############",
        "############",
        "############",
        "############",
        ".##########.",
        "..########..",
        "....####....",
        "............",
    ],
    # A box drawn in axonometric, with the fillet the component offers.
    "Cv_Box": [
        "...++++++++.",
        "..+......+#.",
        ".+++++++++#.",
        ".#.......##.",
        ".#.......##.",
        ".#.......##.",
        ".#.......##.",
        ".#.......##.",
        ".#.......#..",
        ".#########..",
        "............",
        "............",
    ],
    "Cv_Cylinder": [
        "..++++++++..",
        ".+########+.",
        "..++++++++..",
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        ".+########+.",
        "..++++++++..",
        "............",
    ],
    # The gyroid's woven look: two offset strands crossing.
    "Cv_TPMS": [
        "..##....##..",
        ".#..#..#..#.",
        "#....##....#",
        ".#..#..#..#.",
        "..##....##..",
        "............",
        "..##....##..",
        ".#..#..#..#.",
        "#....##....#",
        ".#..#..#..#.",
        "..##....##..",
        "............",
    ],
    # Two overlapping discs, the lens between them filled.
    "Cv_Boolean": [
        "...###......",
        "..#####.....",
        ".###+++##...",
        ".##+++++##..",
        "###+++++###.",
        "###+++++###.",
        "###+++++###.",
        ".##+++++##..",
        ".###+++##...",
        "..#####.....",
        "...###......",
        "............",
    ],
    # A hollow square: the wall is what the component makes.
    "Cv_Shell": [
        "############",
        "############",
        "##........##",
        "##........##",
        "##........##",
        "##........##",
        "##........##",
        "##........##",
        "##........##",
        "##........##",
        "############",
        "############",
    ],
    # A triangulated surface: what comes out of marching cubes.
    "Cv_Mesh": [
        "#....##....#",
        "##..#..#..##",
        "#.##....##.#",
        "#...####...#",
        "##.#....#.##",
        "#.#..##..#.#",
        "#.#..##..#.#",
        "##.#....#.##",
        "#...####...#",
        "#.##....##.#",
        "##..#..#..##",
        "#....##....#",
    ],
    # A magnifier over a part.
    "Cv_Inspect": [
        "...####.....",
        "..#....#....",
        ".#..++..#...",
        ".#.++++.#...",
        ".#.++++.#...",
        ".#..++..#...",
        "..#....#....",
        "...####.##..",
        "........###.",
        ".........###",
        "..........##",
        "............",
    ],
    # A block worn round at the corners.
    "Cv_Abrasion": [
        "............",
        "...######...",
        "..########..",
        ".##########.",
        ".##########.",
        ".##########.",
        ".##########.",
        ".##########.",
        ".##########.",
        "..########..",
        "...######...",
        "............",
    ],
    # A block whose faces stand proud and fall back unevenly.
    "Cv_Differential": [
        "............",
        ".##.###.###.",
        ".#########..",
        "..#########.",
        ".##########.",
        ".########...",
        ".##########.",
        "..#########.",
        ".##########.",
        ".#######.##.",
        ".##.##.#.##.",
        "............",
    ],
    # A face honeycombed with hollows.
    "Cv_Pitting": [
        "############",
        "##..####..##",
        "#....##....#",
        "##..####..##",
        "############",
        "####..######",
        "###....#..##",
        "####..#....#",
        "#..####..###",
        "#...#######.",
        "##.#######..",
        "############",
    ],
    # Beds of alternating width: hard ledges over soft recesses.
    "Cv_Strata": [
        "............",
        ".##########.",
        "...######...",
        ".##########.",
        "############",
        "...######...",
        ".##########.",
        "############",
        "..#######...",
        ".##########.",
        "############",
        "............",
    ],
    # Rain falling on a block, with the gullies it cut.
    "Cv_Runoff": [
        "..+.....+...",
        "...+...+....",
        "............",
        "####.###.###",
        "####.###.###",
        "#####.##.###",
        "#####.#.####",
        "######.#####",
        "######.#####",
        "############",
        "############",
        "............",
    ],
    # A mass split into blocks along open seams.
    "Cv_Jointing": [
        "............",
        ".####.#####.",
        ".####.#####.",
        ".####.#####.",
        "............",
        ".#######.##.",
        ".#######.##.",
        ".#######.##.",
        "............",
        ".###.######.",
        ".###.######.",
        "............",
    ],
    # A coral head folding into lobes.
    "Cv_Fingering": [
        "..##....##..",
        ".####..####.",
        ".####..####.",
        "..###..###..",
        "...######...",
        ".##.####.##.",
        "####.##.####",
        "####.##.####",
        ".##########.",
        "..########..",
        "....####....",
        "............",
    ],
    # A hollow filling up with deposit.
    "Cv_Accretion": [
        "............",
        "............",
        "##........##",
        "##+......+##",
        "###++..++###",
        "###++++++###",
        "####++++####",
        "############",
        "############",
        "############",
        "############",
        "............",
    ],
    # A trunk splitting into twigs.
    "Cv_Branching": [
        "#.....#...#.",
        ".#...#...#..",
        "..#.#...#...",
        "...#...#..#.",
        "...#..#..#..",
        "....#.#.#...",
        ".....###....",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "....####....",
        "............",
    ],
    # Two interpenetrating phases, neither in cells.
    "Cv_Spinodal": [
        "##..###..###",
        "#...##....##",
        "...###..#...",
        "..####.###..",
        "#..##..###.#",
        "##.....##..#",
        "###..#....##",
        ".##.###..###",
        "....###..##.",
        "#....#...#..",
        "##..###.....",
        "###.####..##",
    ],
    # Spots, the simplest Gray-Scott pattern.
    "Cv_ReactionDiffusion": [
        "##..##..##..",
        "##..##..##..",
        "............",
        "..##..##..##",
        "..##..##..##",
        "............",
        "##..##..##..",
        "##..##..##..",
        "............",
        "..##..##..##",
        "..##..##..##",
        "............",
    ],
    # A solid with its thin spikes, in grey, about to be removed.
    "Cv_Morphology": [
        "............",
        ".#####......",
        ".#####......",
        ".#####..+...",
        ".######++++.",
        ".#####......",
        ".#####......",
        ".#####..+...",
        ".######++++.",
        ".#####......",
        ".#####......",
        "............",
    ],
}


def png(pixels, width, height):
    """Encode RGBA rows as a PNG.

    Written out rather than pulled from an image library because the only
    thing needed here is the one uncompressed-filter case, and this keeps the
    script runnable in any interpreter the repository already requires.
    """
    raw = b"".join(b"\x00" + bytes(v for pixel in row for v in pixel) for row in pixels)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def render(sketch):
    """Turn a list of 12 strings into 24x24 rows of RGBA tuples."""
    if len(sketch) != SIZE or any(len(row) != SIZE for row in sketch):
        raise ValueError("Every sketch must be {0}x{0} characters.".format(SIZE))
    rows = []
    for line in sketch:
        row = [PALETTE[c] for c in line for _ in range(SCALE)]
        rows.extend([row] * SCALE)
    return rows


def main():
    for name, sketch in sorted(ICONS.items()):
        folder = os.path.join(COMPONENTS, name)
        if not os.path.isdir(folder):
            raise SystemExit("No component folder for {}: {}".format(name, folder))
        target = os.path.join(folder, "icon.png")
        with open(target, "wb") as f:
            f.write(png(render(sketch), SIZE * SCALE, SIZE * SCALE))
        print("wrote {}".format(os.path.relpath(target, os.path.join(HERE, os.pardir))))

    missing = sorted(set(os.listdir(COMPONENTS)) - set(ICONS) - {"__pycache__"})
    if missing:
        raise SystemExit("These components have no sketch: {}".format(", ".join(missing)))


if __name__ == "__main__":
    main()
