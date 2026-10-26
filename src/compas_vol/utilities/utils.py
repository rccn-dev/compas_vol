__all__ = [
    "get_iso_mesh",
    "get_iso_vfs",
]


def get_iso_vfs(distobj, bounds, resolution=None):
    """Iso-surface an object into vertices and faces.

    Parameters
    ----------
    distobj : :class:`compas_vol.base.VolObject` | str
        The object to mesh, or a COMPAS JSON string describing one.
    bounds : sequence
        Either the COMPAS 1 form ``[(xmin, xmax, nx), (ymin, ymax, ny),
        (zmin, zmax, nz)]``, which carries its own resolution, or anything
        :func:`compas_vol.meshing.normalize_bounds` accepts.
    resolution : int | tuple[int, int, int], optional
        Required unless the resolution is embedded in ``bounds``.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    from compas_vol.meshing import generate_vertices_and_faces

    obj, domain, res = _resolve_iso_args(distobj, bounds, resolution)
    return generate_vertices_and_faces(obj, domain, res)


def get_iso_mesh(distobj, bounds, resolution=None):
    """Iso-surface an object into a COMPAS mesh.

    Accepts and returns the same things as :func:`get_iso_vfs`, but builds a
    :class:`compas.datastructures.Mesh`. In COMPAS 1 both of these were
    hard-wired to reconstruct a :class:`VolBox` from a data dictionary, so they
    only ever worked for boxes.

    Returns
    -------
    :class:`compas.datastructures.Mesh`
    """
    from compas_vol.meshing import generate_mesh

    obj, domain, res = _resolve_iso_args(distobj, bounds, resolution)
    return generate_mesh(obj, domain, res)


def _resolve_iso_args(distobj, bounds, resolution):
    """Accept both the COMPAS 1 and the current calling conventions."""
    from compas.data import json_loads

    obj = json_loads(distobj) if isinstance(distobj, str) else distobj

    if resolution is None and not isinstance(bounds, (int, float)):
        values = list(bounds)
        if len(values) == 3 and all(hasattr(v, "__len__") and len(v) == 3 for v in values):
            # COMPAS 1 form: (min, max, count) per axis.
            domain = [(v[0], v[1]) for v in values]
            res = tuple(int(v[2]) for v in values)
            return obj, domain, res

    if resolution is None:
        raise ValueError("resolution is required unless bounds carries a count per axis")
    return obj, bounds, resolution
