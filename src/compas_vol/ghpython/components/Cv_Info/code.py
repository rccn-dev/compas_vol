"""
Report what compas_vol can do inside this Rhino, and what is missing.

Run this first. Rhino 8 carries its own CPython, so a compas_vol that works in
a terminal says nothing about this document: the package and its optional
dependencies have to be installed into Rhino's interpreter as well.

    Args:
        refresh: Toggle to re-check after installing something.
    Returns:
        report: Version, context and one line per optional dependency.
        context: "rhino" here, "viewer" or "headless" outside.
        ready: True when meshing is available, which is the minimum for
            anything visible to come out of these components.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class CompasVolInfo(component):
    def RunScript(self, refresh: bool):
        ghenv.Component.Message = "compas_vol {{version}}"

        try:
            from compas_vol import nodes
        except ImportError as error:
            return (
                "compas_vol is not importable from Rhino's Python.\n"
                "Build the components with `scripts/ghuser dev` in a compas_vol checkout,\n"
                "which points them at that checkout, or see docs/grasshopper.rst.\n"
                "Underlying error: {}".format(error),
                "none",
                False,
            )

        return nodes.info(refresh)
