"""
A cylinder as a signed distance field.

    Args:
        plane: The cylinder's frame, at its mid-height. Defaults to world XY.
        radius: Radius, in model units.
        height: Total height, in model units.
    Returns:
        vol: A volumetric object, to combine or to mesh.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolCylinder(component):
    def RunScript(self, plane, radius: float, height: float):
        from compas_vol import nodes
        from compas_vol.ghpython import plane_to_frame

        return nodes.cylinder(plane_to_frame(plane), radius, height)
