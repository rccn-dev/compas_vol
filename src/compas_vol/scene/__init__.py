"""
********************************************************************************
compas_vol.scene
********************************************************************************

.. currentmodule:: compas_vol.scene

Scene object plugins for visualizing volumetric objects.

Registration follows the COMPAS 2 pattern: the volumetric classes themselves
know nothing about drawing, and each context declares separately how to draw
them. COMPAS discovers this module through the ``__all_plugins__`` declaration
in :mod:`compas_vol`, the same mechanism ``compas_viewer`` uses for its own
scene objects.

Only the ``Viewer`` context is implemented. Rhino, Blender and Grasshopper
could be added here in exactly the same way.

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    VolObjectSceneObject

"""

from compas.plugins import plugin
from compas.scene import register

from compas_vol.base import VolObject

__all__ = ["VolObjectSceneObject"]


@plugin(category="factories", requires=["compas_viewer"])
def register_scene_objects():
    from .volobject import VolObjectSceneObject

    # Registration resolves through the MRO, so registering the base class
    # covers every primitive, combination, modification and microstructure.
    register(VolObject, VolObjectSceneObject, context="Viewer")


def __getattr__(name):
    # Expose VolObjectSceneObject lazily, so that importing compas_vol.scene
    # does not hard-require compas_viewer.
    if name == "VolObjectSceneObject":
        from .volobject import VolObjectSceneObject

        return VolObjectSceneObject
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
