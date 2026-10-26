"""Shared base class and helpers for all volumetric objects."""

from compas.data import Data
from compas.geometry import Point
from compas.geometry import matrix_from_frame
from compas.geometry import matrix_inverse
from compas.tolerance import TOL

__all__ = [
    "VolObject",
    "reduce_distances",
    "inverse_matrix_from_frame",
    "transform_numpy",
    "format_number",
    "broadcast_distances",
]


def broadcast_distances(distances, x, y, z):
    """Broadcast a list of distance arrays to the common grid shape.

    Distance functions are free to return something smaller than the full grid
    when their result does not depend on every axis -- a :class:`VolPlane` with
    a normal of ``(1, 0, 0)`` queried on an ``ogrid`` returns shape
    ``(nx, 1, 1)``. Reducing a list of such mismatched arrays directly raises,
    so anything that combines several objects has to line them up first.

    Parameters
    ----------
    distances : list[:class:`numpy.ndarray`]
        The per-object distance arrays.
    x, y, z : :class:`numpy.ndarray`
        The coordinate arrays the distances were computed from.

    Returns
    -------
    list[:class:`numpy.ndarray`]
        The distance arrays, each broadcast to the full grid shape.
    """
    import numpy as np

    shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
    return [np.broadcast_to(d, shape) for d in distances]


def reduce_distances(operation, objects, x, y, z):
    """Combine the fields of several objects, one at a time.

    Evaluating every child into its own array and reducing the list afterwards
    needs memory for all of them at once: a union of a few hundred spheres over
    a few million samples runs into gigabytes, and inside threaded sampling
    that is multiplied again by the thread count. Accumulating keeps two arrays
    alive instead of N. ``min`` and ``max`` do not care in what order they see
    their arguments, so the result is identical either way.

    Parameters
    ----------
    operation : callable
        ``numpy.minimum`` for a union, ``numpy.maximum`` for an intersection.
    objects : sequence[:class:`VolObject`]
        The children to combine.
    x, y, z : :class:`numpy.ndarray`
        Coordinate arrays.

    Returns
    -------
    :class:`numpy.ndarray`
    """
    import numpy as np

    if not objects:
        raise ValueError("Nothing to combine: this object has no children.")

    shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
    combined = np.broadcast_to(objects[0].get_distance_numpy(x, y, z), shape).astype(float, copy=True)
    for child in objects[1:]:
        operation(combined, np.broadcast_to(child.get_distance_numpy(x, y, z), shape), out=combined)
    return combined


def format_number(number, precision=None):
    """Format a float for use in ``__repr__``.

    COMPAS 2 replaced the module level ``compas.PRECISION`` string with the
    :class:`compas.tolerance.Tolerance` singleton ``TOL``.
    """
    return TOL.format_number(number, precision=precision)


def inverse_matrix_from_frame(frame):
    """The 4x4 matrix mapping world coordinates into the local space of ``frame``."""
    return matrix_inverse(matrix_from_frame(frame))


def transform_numpy(matrix, x, y, z):
    """Apply a 4x4 transformation matrix to broadcastable coordinate arrays.

    The old implementation built ``np.array([x, y, z, 1], dtype=object)`` and
    handed that to ``np.dot``. That relied on object-dtype broadcasting, which
    is slow, and the variants without ``dtype=object`` raise outright on
    NumPy 2 because the ``ogrid`` components have inhomogeneous shapes.
    Expanding the matrix-vector product by hand keeps everything in float64 and
    lets NumPy broadcast ``(nx, 1, 1)``, ``(1, ny, 1)`` and ``(1, 1, nz)``
    against each other the way it normally would.

    Parameters
    ----------
    matrix : list[list[float]]
        A 4x4 transformation matrix.
    x, y, z : :class:`numpy.ndarray`
        Coordinate arrays, typically from ``np.ogrid[...]``.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`, :class:`numpy.ndarray`]
        The transformed coordinates. Each is broadcast only over the inputs
        it depends on: with an axis-aligned frame and ``ogrid`` inputs, the
        transformed ``x`` stays ``(nx, 1, 1)``. A plan shape -- an extrusion,
        say -- then costs one evaluation per plan point instead of one per
        voxel, which over a slab 30 voxels deep is 30 times less work.
        Callers that need a common shape take ``np.broadcast_shapes``.
    """
    import numpy as np

    m = matrix
    coordinates = (x, y, z)

    def row(i):
        # Terms with a zero coefficient are left out rather than multiplied
        # by zero, which would broadcast the result over an axis it does not
        # depend on.
        value = m[i][3]
        for coefficient, coordinate in zip(m[i][:3], coordinates):
            if coefficient != 0:
                value = value + coefficient * coordinate
        return np.asarray(value, dtype=float)

    return row(0), row(1), row(2)


class VolObject(Data):
    """Base class for every volumetric object.

    A volumetric object is defined by a signed distance function: negative
    inside the solid, zero on its boundary, positive outside. Subclasses
    implement :meth:`get_distance` for a single point and
    :meth:`get_distance_numpy` for a whole grid at once.

    Subclassing :class:`compas.data.Data` is what gives every object
    ``__data__``-based JSON serialisation, ``copy()`` and a ``guid``. The
    COMPAS 1 ``to_data``/``from_data`` pair this package used to hand-roll no
    longer exists in COMPAS 2.
    """

    def get_distance(self, point):
        """The signed distance from a single point to the surface of the object.

        Parameters
        ----------
        point : :class:`compas.geometry.Point` | list[float]
            The query point.

        Returns
        -------
        float
            Negative inside, zero on the boundary, positive outside.
        """
        raise NotImplementedError

    def get_distance_numpy(self, x, y, z):
        """The signed distance for a grid of points.

        Parameters
        ----------
        x, y, z : :class:`numpy.ndarray`
            Coordinate arrays, typically from ``np.ogrid[...]`` with shapes
            ``(nx, 1, 1)``, ``(1, ny, 1)`` and ``(1, 1, nz)``.

        Returns
        -------
        :class:`numpy.ndarray`
            Distances, of shape ``(nx, ny, nz)``.
        """
        raise NotImplementedError

    # ==========================================================================
    # helpers
    # ==========================================================================

    @staticmethod
    def _as_point(point):
        """Coerce a point-like object to a :class:`compas.geometry.Point` copy.

        Always returns a *copy*, so that objects which transform the query
        point into their local space cannot mutate the caller's point. The old
        code did ``p = point`` followed by ``p.transform(...)``, which meant
        calling ``get_distance`` twice with the same Point gave two different
        answers.
        """
        return Point(*point)

    # ==========================================================================
    # operators
    # ==========================================================================

    def __or__(self, other):
        from compas_vol.combinations import Union

        return Union(self, other)

    def __and__(self, other):
        from compas_vol.combinations import Intersection

        return Intersection(self, other)

    def __sub__(self, other):
        from compas_vol.combinations import Subtraction

        return Subtraction(self, other)
