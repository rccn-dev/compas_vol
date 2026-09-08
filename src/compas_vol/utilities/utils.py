import math
import random

from compas.datastructures import Mesh

__all__ = [
    "bbox_edges",
    "export_ipv_mesh",
    "export_layer",
    "export_ski_mesh",
    "get_compas_mesh",
    "get_iso_mesh",
    "get_iso_vfs",
    "get_random_vector_2D",
    "get_random_vector_3D",
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


def export_ski_mesh(vs, fs, ns=None, filename="ski_mesh.obj"):
    """Write vertices, faces and optional normals to an OBJ file."""
    ve = ["v {} {} {}".format(v[0], v[1], v[2]) for v in vs]
    if ns is not None:
        ne = ["vn {} {} {}".format(n[0], n[1], n[2]) for n in ns]
        fe = ["f {0}//{0} {1}//{1} {2}//{2}".format(f[0] + 1, f[1] + 1, f[2] + 1) for f in fs]
    else:
        ne = None
        fe = ["f {} {} {}".format(f[0] + 1, f[1] + 1, f[2] + 1) for f in fs]

    with open(filename, "w") as f:
        f.write("\n".join(ve))
        f.write("\n")
        if ne is not None:
            f.write("\n".join(ne))
            f.write("\n")
        f.write("\n".join(fe))


def export_ipv_mesh(mesh, filename="ipv_mesh.obj", colors=None):
    """Export an ``ipyvolume.widgets.Mesh`` to an OBJ file.

    Retained for notebooks that still use ipyvolume. New code should add the
    volumetric object to a scene directly -- see :mod:`compas_vol.scene`.
    """
    import numpy as np

    vs = np.vstack((mesh.x, mesh.y, mesh.z)).T
    vs = ["v {} {} {}".format(v[0], v[1], v[2]) for v in vs]
    if colors is not None:
        vs = [vs[i] + " {} {} {}".format(c[0], c[1], c[2]) for i, c in enumerate(colors)]
    fs = ["f {} {} {}".format(v[0] + 1, v[1] + 1, v[2] + 1) for v in mesh.triangles]

    with open(filename, "w") as f:
        f.write("\n".join(vs))
        f.write("\n")
        f.write("\n".join(fs))


def get_random_vector_2D():
    """A random unit vector in the XY plane."""
    angle = random.random() * math.pi * 2
    return (math.cos(angle), math.sin(angle))


def get_random_vector_3D(r=1.0):
    """A random vector of length ``r``, uniformly distributed on the sphere."""
    angle = random.random() * math.pi * 2
    vz = random.random() * 2 - 1
    vx = math.sqrt(1 - vz**2) * math.cos(angle)
    vy = math.sqrt(1 - vz**2) * math.sin(angle)
    return (r * vx, r * vy, r * vz)


def get_compas_mesh(v, f):
    """Build a COMPAS mesh from vertices and faces."""
    return Mesh.from_vertices_and_faces(v, f)


def export_layer(distfield, resolution, level, filename="layerimage.png", size=10):
    """Export a horizontal slice through a distance field as an image.

    Requires the ``meshing`` extra for scikit-image.
    """
    import numpy as np
    from skimage import io

    y, x = np.ogrid[-size : size : resolution * 1j, -size : size : resolution * 1j]
    d = distfield.get_distance_numpy(x, y, level)

    # Anti-aliased band around the zero level set.
    m = 1 - (np.tanh(d) + 1) / 2
    io.imsave(filename, np.asarray(m, dtype=float))
    return d


def bbox_edges(a, b, c, d, e, f):
    """The twelve edges of an axis-aligned bounding box, as start/end lists.

    Parameters
    ----------
    a, b : float
        The min and max along X.
    c, d : float
        The min and max along Y.
    e, f : float
        The min and max along Z.

    Returns
    -------
    tuple[list, list]
        Start points and end points of the edges.
    """
    v1 = [a, c, e]
    v2 = [b, c, e]
    v3 = [b, d, e]
    v4 = [a, d, e]
    v5 = [a, c, f]
    v6 = [b, c, f]
    v7 = [b, d, f]
    v8 = [a, d, f]
    vs = [v1, v2, v3, v4, v1, v2, v3, v4, v5, v6, v7, v8]
    ve = [v2, v3, v4, v1, v5, v6, v7, v8, v6, v7, v8, v5]
    return vs, ve
