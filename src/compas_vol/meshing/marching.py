"""Iso-surfacing of volumetric objects via marching cubes."""

from compas.datastructures import Mesh
from compas.geometry import Box

__all__ = [
    "normalize_bounds",
    "sample",
    "generate_vertices_and_faces",
    "generate_mesh",
]


def normalize_bounds(bounds):
    """Coerce a bounds specification to ``(xmin, ymin, zmin, xmax, ymax, zmax)``.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
        A Box, a single number ``s`` meaning the cube ``[-s, s]`` on each axis,
        a 6-sequence ``(xmin, ymin, zmin, xmax, ymax, zmax)``, or a 3-sequence
        of ``(min, max)`` pairs.

    Returns
    -------
    tuple[float, float, float, float, float, float]
    """
    if isinstance(bounds, Box):
        return (
            bounds.xmin,
            bounds.ymin,
            bounds.zmin,
            bounds.xmax,
            bounds.ymax,
            bounds.zmax,
        )

    if isinstance(bounds, (int, float)):
        s = float(bounds)
        return (-s, -s, -s, s, s, s)

    values = list(bounds)
    if len(values) == 6:
        return tuple(float(v) for v in values)
    if len(values) == 3 and all(hasattr(v, "__len__") for v in values):
        (x0, x1), (y0, y1), (z0, z1) = (tuple(v)[:2] for v in values)
        return (float(x0), float(y0), float(z0), float(x1), float(y1), float(z1))

    raise ValueError("Cannot interpret bounds: {!r}".format(bounds))


def _resolution(resolution):
    if isinstance(resolution, (int, float)):
        n = int(resolution)
        return n, n, n
    nx, ny, nz = resolution
    return int(nx), int(ny), int(nz)


def sample(obj, bounds, resolution=64):
    """Sample the distance field of an object on a regular grid.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to sample.
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`normalize_bounds`.
    resolution : int | tuple[int, int, int]
        The number of samples along each axis.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, tuple[float, float, float], tuple[float, float, float]]
        The distance matrix of shape ``(nx, ny, nz)``, the grid origin, and
        the spacing between samples along each axis.
    """
    import numpy as np

    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
    nx, ny, nz = _resolution(resolution)

    x, y, z = np.ogrid[x0 : x1 : nx * 1j, y0 : y1 : ny * 1j, z0 : z1 : nz * 1j]
    dm = np.asarray(obj.get_distance_numpy(x, y, z), dtype=float)
    dm = np.broadcast_to(dm, (nx, ny, nz))

    spacing = (
        (x1 - x0) / (nx - 1),
        (y1 - y0) / (ny - 1),
        (z1 - z0) / (nz - 1),
    )
    return dm, (x0, y0, z0), spacing


def generate_vertices_and_faces(obj, bounds, resolution=64, level=0.0):
    """Iso-surface an object, returning raw vertices and triangular faces.

    Requires the ``meshing`` extra (``pip install compas-vol[meshing]``).

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to mesh.
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`normalize_bounds`.
    resolution : int | tuple[int, int, int]
        The number of samples along each axis.
    level : float
        The iso-value to extract. ``0.0`` is the surface of the object;
        negative values shrink it, positive values grow it.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
        Vertices in world coordinates, and triangular faces.
    """
    # ``marching_cubes_lewiner`` was deprecated in scikit-image 0.19 and
    # removed thereafter; ``marching_cubes`` uses the Lewiner algorithm now.
    from skimage.measure import marching_cubes

    dm, origin, spacing = sample(obj, bounds, resolution)
    verts, faces, _normals, _values = marching_cubes(dm, level, spacing=spacing)

    # marching_cubes returns coordinates relative to the grid corner. The old
    # implementation never added the origin back, so every mesh came out
    # shifted into the positive octant.
    verts = verts + origin
    return verts, faces


def generate_mesh(obj, bounds, resolution=64, level=0.0):
    """Iso-surface an object into a COMPAS mesh.

    Requires the ``meshing`` extra (``pip install compas-vol[meshing]``).

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to mesh.
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`normalize_bounds`.
    resolution : int | tuple[int, int, int]
        The number of samples along each axis.
    level : float
        The iso-value to extract.

    Returns
    -------
    :class:`compas.datastructures.Mesh`

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.meshing import generate_mesh
    >>> mesh = generate_mesh(VolSphere(Sphere(5, point=Point(0, 0, 0))), 8.0, 32)
    >>> mesh.number_of_faces() > 0
    True
    """
    verts, faces = generate_vertices_and_faces(obj, bounds, resolution, level)
    return Mesh.from_vertices_and_faces(verts.tolist(), faces.tolist())
