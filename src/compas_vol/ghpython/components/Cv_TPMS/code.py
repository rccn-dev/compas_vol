"""
A triply periodic minimal surface, thickened into a printable solid.

The surface types are Gyroid, SchwarzP, Diamond, Neovius, Lidinoid,
FischerKoch and IWP. "sheet" thickens the surface itself into a double-sided
wall; "network" fills one of the two interpenetrating channels and leaves the
other open.

cell and thickness are both in model units: this is the metric TPMS, so a
thickness of 2 measures 2 mm on the printed part.

    Args:
        type: Surface name, or its index. Defaults to Gyroid.
        cell: Cell size, the true period of the pattern.
        thickness: Wall thickness, in model units.
        mode: "sheet" or "network". Defaults to sheet.
        plane: Orients and positions the lattice. Defaults to world XY.
    Returns:
        vol: A volumetric object, to combine or to mesh.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolTPMS(component):
    def RunScript(self, type, cell: float, thickness: float, mode: str, plane):
        from compas_vol import nodes
        from compas_vol.ghpython import plane_to_frame

        return nodes.tpms(type, cell, thickness, mode, plane_to_frame(plane))
