"""
A box as a signed distance field, with optionally rounded edges.

    Args:
        plane: The box's frame, at its centre. Defaults to world XY.
        xsize: Size along the frame's X axis.
        ysize: Size along Y. Defaults to xsize.
        zsize: Size along Z. Defaults to xsize.
        radius: Edge fillet radius. 0 leaves the edges sharp.
    Returns:
        vol: A volumetric object, to combine or to mesh.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolBox(component):
    def RunScript(self, plane, xsize: float, ysize: float, zsize: float, radius: float):
        from compas_vol import nodes
        from compas_vol.ghpython import plane_to_frame

        return nodes.box(plane_to_frame(plane), xsize, ysize, zsize, radius)
