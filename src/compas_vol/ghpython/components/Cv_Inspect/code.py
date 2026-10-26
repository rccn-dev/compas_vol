"""
Check a volumetric object for the things that stop a model printing.

Everything is measured on the sampled grid, before any mesh exists: separate
pieces, sealed voids, overhangs, islands that start in mid-air, and walls
thinner than the nozzle can lay down. Raise the resolution until the numbers
stop moving before trusting them -- a thin wall the grid cannot see is a thin
wall this cannot report.

    Args:
        vol: The object to check.
        bounds: The box to sample over, as for the Mesh component.
        resolution: Samples per axis. Defaults to 96.
        angle: Overhang threshold from vertical, in degrees. Defaults to 45.
        min_wall: Thinnest printable wall, in model units. Defaults to 1.6.
    Returns:
        report: The findings, as text.
        ok: True when nothing was found that would stop the print.
        pieces: Separate solids. More than one and this is not a single part.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolInspect(component):
    def RunScript(self, vol, bounds, resolution: int, angle: float, min_wall: float):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        return nodes.inspect(vol, box_to_bounds(bounds), resolution, angle, min_wall)
