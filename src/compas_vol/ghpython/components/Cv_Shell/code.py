"""
Hollow a volumetric object out into a shell of even thickness.

The wall is centred on the original surface, so half the thickness lies
inside it and half outside.

    Args:
        vol: The object to hollow.
        thickness: Wall thickness, in model units.
    Returns:
        shell: A volumetric object, to combine or to mesh.

Note: thickness is only measured in model units if the field is metric.
Primitives and booleans of them are; a TPMS field scaled by Remap, or
anything multiplied, is not.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolShell(component):
    def RunScript(self, vol, thickness: float):
        from compas_vol import nodes

        return nodes.shell(vol, thickness)
