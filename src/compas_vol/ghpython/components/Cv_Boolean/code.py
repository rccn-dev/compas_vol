"""
Combine volumetric objects.

operation is one of union, intersection or difference. A blend radius above 0
switches to the smooth variant, which fillets the seam over that distance
instead of leaving a crease. difference subtracts every later object from the
first.

    Args:
        vols: Two or more volumetric objects.
        operation: "union", "intersection" or "difference". Defaults to union.
        blend: Fillet radius at the seam, in model units. 0 is a hard boolean.
    Returns:
        vol: A volumetric object, to combine further or to mesh.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolBoolean(component):
    def RunScript(self, vols, operation: str, blend: float):
        from compas_vol import nodes

        return nodes.boolean(vols, operation, blend)
