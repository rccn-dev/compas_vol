"""Signed distance to a closed triangle mesh, sampled onto a grid.

This is how arbitrary geometry gets into the field world. ``VolPolyhedron``
only handles convex solids, so until now anything modelled as a mesh -- a
survey, a NURBS skin tessellated in Rhino, a form-found shell from
``compas_tess`` -- could not be used as a field at all.

Two halves, with different methods because they have different difficulties:

**Magnitude** is the distance to the nearest point of the surface. The
surface is sampled into a dense point cloud and queried with a KD-tree, which
is exact at the samples and slightly over-estimates between them. The error
is bounded by how far apart the samples are, so :func:`surface_samples`
subdivides every triangle until its samples are closer together than the
voxel -- at which point the error is below the resolution of the grid it is
being written into, and invisible.

**Sign** is inside or outside, and approximating that is not acceptable: one
wrong cell is a hole in the solid. It is computed exactly, by counting how
many triangles lie above each grid column. A closed surface is crossed an odd
number of times from any interior point and an even number from outside, so
the parity of that count is the answer, and it needs no tolerance.
"""

import numpy as np

from compas_vol.runtime import require

__all__ = ["signed_distance_to_mesh", "surface_samples"]


def _triangles(mesh):
    """The mesh as an ``(n, 3, 3)`` array of triangle corners.

    Faces with more than three corners are fanned. The fan is only used for
    distance and crossing counts, never for topology, so a non-planar quad
    costs nothing here.
    """
    vertices, faces = mesh.to_vertices_and_faces()
    points = np.asarray(vertices, dtype=float)
    corners = []
    for face in faces:
        for i in range(1, len(face) - 1):
            corners.append((face[0], face[i], face[i + 1]))
    if not corners:
        raise ValueError("The mesh has no faces.")
    return points[np.asarray(corners, dtype=int)]


def surface_samples(triangles, spacing):
    """Points covering the surface no more than ``spacing`` apart.

    Each triangle is split into a regular barycentric grid fine enough that
    neighbouring samples are closer than ``spacing``. Returning the corners
    alone would under-sample a large triangle and report a point at its centre
    as further from the surface than it is.

    Parameters
    ----------
    triangles : :class:`numpy.ndarray`
        Shape ``(n, 3, 3)``.
    spacing : float
        Target distance between samples, in model units.

    Returns
    -------
    :class:`numpy.ndarray`
        Shape ``(m, 3)``.
    """
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    longest = np.maximum.reduce([
        np.linalg.norm(b - a, axis=1),
        np.linalg.norm(c - b, axis=1),
        np.linalg.norm(a - c, axis=1),
    ])
    divisions = np.maximum(1, np.ceil(longest / max(spacing, 1e-9)).astype(int))

    points = [triangles.reshape(-1, 3)]
    # Triangles needing the same subdivision are done in one vectorized pass,
    # so the Python loop runs once per distinct level rather than per triangle.
    for n in np.unique(divisions):
        if n < 2:
            continue
        group = triangles[divisions == n]
        us, vs = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing="ij")
        keep = (us + vs) <= n
        u = (us[keep] / n)[None, :, None]
        v = (vs[keep] / n)[None, :, None]
        points.append(
            (group[:, 0][:, None, :] * (1.0 - u - v)
             + group[:, 1][:, None, :] * u
             + group[:, 2][:, None, :] * v).reshape(-1, 3)
        )
    return np.unique(np.concatenate(points), axis=0)


def _inside(triangles, origin, spacing, shape):
    """Which grid cells are inside the closed surface.

    A ray is cast from each grid column along +Z and the triangles it passes
    through are counted. Every crossing flips inside to outside, so the number
    of crossings strictly below a node decides it: odd is inside.

    The rays start at the grid nodes themselves, not at cell centres: the
    distances this sign is applied to are sampled at the nodes, and a mask
    computed half a voxel away would be a mask of a different grid. They are
    nudged by a small fraction of a voxel so that a ray cannot run exactly
    along a shared triangle edge, where it would be counted twice or not at
    all. The nudge is deliberately not a round fraction, so it cannot line up
    with a model built on a round grid.
    """
    nx, ny, nz = shape
    # The two nudges differ, and are irrational multiples of each other. An
    # equal nudge moves the ray along the (1, 1) diagonal, which is exactly
    # where a fanned quad puts its shared edge -- the ray then stays on that
    # edge, is counted by both triangles, and the cell reads inside-out. That
    # is not a corner case: it is every axis-aligned box in the package.
    x = origin[0] + (np.arange(nx) + 1e-3 * np.sqrt(2.0)) * spacing[0]
    y = origin[1] + (np.arange(ny) + 1e-3 * np.sqrt(5.0)) * spacing[1]
    crossings = np.zeros(shape, dtype=np.int32)

    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    # Barycentric coordinates of a column against each triangle's XY shadow.
    e1 = b[:, :2] - a[:, :2]
    e2 = c[:, :2] - a[:, :2]
    det = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
    usable = np.abs(det) > 1e-12          # edge-on triangles cross no column
    if not usable.any():
        return np.zeros(shape, dtype=bool)

    a, b, c = a[usable], b[usable], c[usable]
    e1, e2, det = e1[usable], e2[usable], det[usable]

    lo = np.minimum.reduce([a[:, :2], b[:, :2], c[:, :2]])
    hi = np.maximum.reduce([a[:, :2], b[:, :2], c[:, :2]])

    for t in range(len(a)):
        # Only the columns under this triangle's bounding box can be hit.
        i0 = np.searchsorted(x, lo[t, 0], side="left")
        i1 = np.searchsorted(x, hi[t, 0], side="right")
        j0 = np.searchsorted(y, lo[t, 1], side="left")
        j1 = np.searchsorted(y, hi[t, 1], side="right")
        if i0 >= i1 or j0 >= j1:
            continue

        px = x[i0:i1, None] - a[t, 0]
        py = y[None, j0:j1] - a[t, 1]
        u = (px * e2[t, 1] - py * e2[t, 0]) / det[t]
        v = (py * e1[t, 0] - px * e1[t, 1]) / det[t]
        hit = (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0)
        if not hit.any():
            continue

        # Height of the surface at each hit, as the first node above it.
        zs = a[t, 2] + u * (b[t, 2] - a[t, 2]) + v * (c[t, 2] - a[t, 2])
        level = np.floor((zs - origin[2]) / spacing[2]).astype(int) + 1
        np.clip(level, 0, nz, out=level)

        ii, jj = np.nonzero(hit)
        # One crossing below every node from `level` upward: add at the level
        # and take a running sum along Z at the end.
        counted = level[ii, jj]
        keep = counted < nz
        np.add.at(crossings, (ii[keep] + i0, jj[keep] + j0, counted[keep]), 1)

    return (np.cumsum(crossings, axis=2) % 2).astype(bool)


def signed_distance_to_mesh(mesh, origin, spacing, shape, samples=None):
    """Signed distance from every cell of a grid to a closed mesh.

    Parameters
    ----------
    mesh : :class:`compas.datastructures.Mesh`
        A closed surface. An open one still returns a field, but the sign is
        then meaningless, because "inside" is not defined.
    origin : sequence[float]
        World coordinates of cell ``(0, 0, 0)``.
    spacing : sequence[float]
        Cell size along each axis.
    shape : sequence[int]
        Cells along each axis.
    samples : :class:`numpy.ndarray`, optional
        Pre-computed surface samples, to avoid rebuilding them.

    Returns
    -------
    :class:`numpy.ndarray`
        Shape ``shape``, negative inside.
    """
    spatial = require("scipy.spatial")

    triangles = _triangles(mesh)
    if samples is None:
        samples = surface_samples(triangles, 0.5 * min(spacing))

    grid = np.stack(np.meshgrid(
        *(origin[i] + np.arange(shape[i]) * spacing[i] for i in range(3)), indexing="ij"
    ), axis=-1).reshape(-1, 3)

    distance, _ = spatial.cKDTree(samples).query(grid, k=1)
    distance = distance.reshape(shape)

    inside = _inside(triangles, origin, spacing, tuple(shape))
    return np.where(inside, -distance, distance)
