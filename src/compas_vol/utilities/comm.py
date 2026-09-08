"""Transport helpers for evaluating volumetric objects in another process.

The COMPAS 1 version shipped an object as its ``repr`` string and rebuilt it
with ``eval``, which executes whatever it is handed. COMPAS 2's data model
serialises every :class:`compas_vol.base.VolObject` to JSON, so the object can
be moved without granting the sender code execution.
"""

from compas.data import json_dumps
from compas.data import json_loads

__all__ = ["dumps_tree", "loads_tree", "get_vfs_from_tree"]


def dumps_tree(obj):
    """Serialise a volumetric object tree to a JSON string.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to serialise, including all of its children.

    Returns
    -------
    str
    """
    return json_dumps(obj)


def loads_tree(data):
    """Rebuild a volumetric object tree from a JSON string.

    Parameters
    ----------
    data : str
        A JSON string produced by :func:`dumps_tree`.

    Returns
    -------
    :class:`compas_vol.base.VolObject`
    """
    return json_loads(data)


def get_vfs_from_tree(tree, bounds, resolution=None):
    """Mesh a serialised object tree, for use over COMPAS RPC.

    Parameters
    ----------
    tree : str | :class:`compas_vol.base.VolObject`
        A JSON string from :func:`dumps_tree`, or the object itself.
    bounds : sequence
        Either the COMPAS 1 form ``[(xmin, xmax, nx), ...]``, or anything
        :func:`compas_vol.meshing.normalize_bounds` accepts.
    resolution : int | tuple[int, int, int], optional
        Required unless the resolution is embedded in ``bounds``.

    Returns
    -------
    tuple[list, list]
        Vertices and faces, as plain lists so they survive an RPC round trip.
    """
    from compas_vol.utilities.utils import get_iso_vfs

    obj = loads_tree(tree) if isinstance(tree, str) else tree
    verts, faces = get_iso_vfs(obj, bounds, resolution)
    return verts.tolist(), faces.tolist()
