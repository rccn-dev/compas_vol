"""Iso-surfacing of volumetric objects via marching cubes."""

import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from compas_vol.runtime import require
from compas.datastructures import Mesh
from compas.geometry import Box

__all__ = [
    "normalize_bounds",
    "sample",
    "iso_surface",
    "is_watertight",
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


def _workers(workers):
    if workers is None:
        return min(os.cpu_count() or 1, 32)
    return max(1, int(workers))


def sample(obj, bounds, resolution=64, workers=None):
    """Sample the distance field of an object on a regular grid.

    The grid is evaluated in slabs along X, in parallel. NumPy releases the
    GIL inside its own operations, so threads give real parallelism here:
    about 5x on ten cores for an analytic field, 3x for one whose Python-level
    loop is the cost. Slabs are independent and each writes its own rows, so
    the result is identical to the serial one, bit for bit.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to sample.
    bounds : :class:`compas.geometry.Box` | float | sequence
        The sampling domain. See :func:`normalize_bounds`.
    resolution : int | tuple[int, int, int]
        The number of samples along each axis.
    workers : int, optional
        Threads to use. Defaults to the number of cores; pass ``1`` to sample
        serially.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, tuple[float, float, float], tuple[float, float, float]]
        The distance matrix of shape ``(nx, ny, nz)``, the grid origin, and
        the spacing between samples along each axis.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.meshing import sample
    >>> dm, origin, spacing = sample(VolSphere(Sphere(5, point=Point(0, 0, 0))), 8.0, 32)
    >>> dm.shape
    (32, 32, 32)
    """
    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
    nx, ny, nz = _resolution(resolution)

    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)[None, :, None]
    zs = np.linspace(z0, z1, nz)[None, None, :]

    field = np.empty((nx, ny, nz), dtype=float)

    def evaluate(rows):
        lo, hi = rows
        field[lo:hi] = obj.get_distance_numpy(xs[lo:hi, None, None], ys, zs)

    workers = _workers(workers)
    # A few slabs per worker, so that an uneven field (a Voronoi cell here, an
    # empty region there) does not leave threads idle at the end.
    slabs = min(nx, 4 * workers) if workers > 1 else 1
    edges = np.linspace(0, nx, slabs + 1).astype(int)
    ranges = [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]

    if len(ranges) == 1:
        evaluate(ranges[0])
    else:
        with ThreadPoolExecutor(workers) as pool:
            list(pool.map(evaluate, ranges))

    spacing = (
        (x1 - x0) / (nx - 1),
        (y1 - y0) / (ny - 1),
        (z1 - z0) / (nz - 1),
    )
    return field, (x0, y0, z0), spacing


def iso_surface(values, origin=(0, 0, 0), spacing=(1, 1, 1), level=0.0):
    """Iso-surface a grid of values that has already been sampled.

    The half of :func:`generate_vertices_and_faces` that does not sample, for
    when the grid came from somewhere else: a process, a repair, a field
    edited in place.

    Requires the ``meshing`` extra (``pip install compas-vol[meshing]``).

    Parameters
    ----------
    values : array-like
        The field, shape ``(nx, ny, nz)``, negative inside.
    origin : sequence[float]
        World coordinates of ``values[0, 0, 0]``.
    spacing : sequence[float]
        Sample spacing along each axis.
    level : float
        The iso-value to extract.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
        Vertices in world coordinates, and triangular faces, wound so that
        their normals point out of the solid.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.meshing import iso_surface
    >>> x, y, z = np.ogrid[-8:8:33j, -8:8:33j, -8:8:33j]
    >>> vertices, faces = iso_surface(np.sqrt(x**2 + y**2 + z**2) - 5.0, (-8, -8, -8), (0.5, 0.5, 0.5))
    >>> bool(abs(np.linalg.norm(vertices, axis=1).mean() - 5.0) < 0.05)
    True
    """
    # ``marching_cubes_lewiner`` was deprecated in scikit-image 0.19 and
    # removed thereafter; ``marching_cubes`` uses the Lewiner algorithm now.
    marching_cubes = require("skimage.measure").marching_cubes

    values = np.asarray(values, dtype=float)
    # A sample on the level, or within a hair of it -- every sample of a face
    # lying on a grid plane, like a slab soffit at z = 0 -- puts the vertices
    # of several cube edges at the same point. Marching cubes then emits
    # zero-area triangles, and an STL reader welds the coincident vertices
    # into non-manifold edges. Holding every sample at least a thousandth of
    # a voxel from the level, on its own side, keeps vertices apart and moves
    # the surface by no more than that.
    gap = 1e-3 * min(spacing)
    close = np.abs(values - level) < gap
    if close.any():
        values = np.where(close, level + np.where(values < level, -gap, gap), values)
    vertices, faces, _normals, _values = marching_cubes(values, level, spacing=spacing)

    # marching_cubes returns coordinates relative to the grid corner. The old
    # implementation never added the origin back, so every mesh came out
    # shifted into the positive octant.
    return vertices + origin, faces


def is_watertight(vertices, faces):
    """Whether a triangle mesh is closed and manifold once written as STL and read back.

    STL stores loose triangles in single precision, and a reader joins corners
    with identical coordinates. Every edge must then be shared by exactly two
    triangles, or a slicer reports the part as broken: an edge used once is a
    hole, an edge used three times or more is non-manifold. Checking the
    welded single-precision corners rather than the vertex indices is what
    makes this the slicer's answer rather than the mesher's.

    Parameters
    ----------
    vertices : array-like
        ``(n, 3)`` coordinates.
    faces : array-like
        ``(m, 3)`` vertex indices.

    Returns
    -------
    bool

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.meshing import is_watertight
    >>> vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    >>> faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]])
    >>> is_watertight(vertices, faces), is_watertight(vertices, faces[:3])
    (True, False)
    """
    faces = np.asarray(faces)
    if not len(faces):
        return False
    _, welded = np.unique(np.asarray(vertices, dtype=np.float32), axis=0, return_inverse=True)
    corners = welded.reshape(-1)[faces]
    edges = np.sort(np.concatenate([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return bool((counts == 2).all())


def generate_vertices_and_faces(obj, bounds, resolution=64, level=0.0, workers=None):
    """Sample an object and iso-surface it, returning vertices and faces.

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
    workers : int, optional
        Threads used for sampling. See :func:`sample`.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
        Vertices in world coordinates, and triangular faces, wound so that
        their normals point out of the solid.
    """
    values, origin, spacing = sample(obj, bounds, resolution, workers=workers)
    return iso_surface(values, origin, spacing, level)


def generate_mesh(obj, bounds, resolution=64, level=0.0, workers=None):
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
    workers : int, optional
        Threads used for sampling. See :func:`sample`.

    Returns
    -------
    :class:`compas.datastructures.Mesh`

    Notes
    -----
    Building a COMPAS mesh from millions of triangles costs more than the
    sampling and the iso-surfacing together, because it is a Python-level
    data structure. To write a file for printing, use
    :func:`compas_vol.meshing.export_stl` instead, which goes from the field
    to the file through arrays only.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.meshing import generate_mesh
    >>> mesh = generate_mesh(VolSphere(Sphere(5, point=Point(0, 0, 0))), 8.0, 32)
    >>> mesh.number_of_faces() > 0
    True
    """
    verts, faces = generate_vertices_and_faces(obj, bounds, resolution, level, workers=workers)
    return Mesh.from_vertices_and_faces(verts.tolist(), faces.tolist())
