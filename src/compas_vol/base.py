"""Shared base class and helpers for all volumetric objects."""

from compas.data import Data
from compas.geometry import Point
from compas.geometry import matrix_from_frame
from compas.geometry import matrix_inverse
from compas.tolerance import TOL

__all__ = [
    "VolObject",
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
        The transformed coordinates, broadcast to a common shape.
    """
    m = matrix
    xt = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3]
    yt = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3]
    zt = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3]
    return xt, yt, zt


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
