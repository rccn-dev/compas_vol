# r: scikit-fmm>=2025.1.29
"""
Growth that folds into lobes and valleys: the brain-coral mechanism.

A bulge grows faster than the surface beside it and becomes a lobe;
lobes that meet simply merge. The surface grows outward, so leave height
of room around the model or the folds are cut at the box. A finer
resolution takes longer and folds more finely, but grows as far.

    Args:
        vol: The starting solid. A process result runs on its own grid when
            bounds is unwired.
        bounds: The box to sample vol over. Leave unwired to run on a process
            result's own grid.
        resolution: Samples per axis. Defaults to 64. Sets the finest feature:
            below two voxels, nothing survives.
        height: Millimetres the fastest part of the surface advances. Defaults
            to 30.
        length: Length curvature is measured against, in mm. Defaults to 9.
        gain: Strength of the folding. 0 grows evenly; past 1.5 lobes pinch
            off. Defaults to 1.4.
        wavelength: Roughly the width of a fold, in mm. Defaults to 4.
        run: False holds the last result while you change things upstream.
            Unwired, it runs.
    Returns:
        result: The result: a volumetric object to combine, run another process
            on, or mesh.
        history: How it was made, one operation per line.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolFingering(component):
    def RunScript(
        self,
        vol,
        bounds,
        resolution: int,
        height: float,
        length: float,
        gain: float,
        wavelength: float,
        run: bool,
    ):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds

        # The script instance survives between solutions, so it can hold a result.
        if run is not False:
            self.held = nodes.fingering(vol, box_to_bounds(bounds), resolution, height, length, gain, wavelength, run)
        return getattr(self, "held", (None, None))
