"""
A sphere as a signed distance field.

    Args:
        point: Centre. Defaults to the world origin.
        radius: Radius, in model units.
    Returns:
        vol: A volumetric object, to combine or to mesh.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolSphere(component):
    def RunScript(self, point, radius: float):
        from compas_vol import nodes
        from compas_vol.ghpython import point_to_compas

        return nodes.sphere(point_to_compas(point), radius)
