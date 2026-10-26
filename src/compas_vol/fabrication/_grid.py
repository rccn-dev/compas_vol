"""Shared plumbing for the fabrication checks and repairs."""

import numpy as np

from compas_vol.runtime import require

__all__ = ["face_connectivity", "unpack", "largest_piece"]


def face_connectivity():
    """Two voxels are one piece only if they share a face.

    Meeting at an edge or a corner is a point contact, which is not a
    connection anything can be printed through.
    """
    ndimage = require("scipy.ndimage")

    return ndimage.generate_binary_structure(3, 1)


def unpack(solid, spacing=None, origin=None):
    """Accept a Field, a VolGrid, or a plain array with its grid."""
    values = getattr(solid, "values", solid)
    spacing = spacing or getattr(solid, "spacing", None)
    origin = origin or getattr(solid, "origin", (0.0, 0.0, 0.0))
    if spacing is None:
        raise ValueError("Pass a Field or a VolGrid, or give `spacing` with the array.")
    return np.asarray(values, dtype=float), tuple(spacing), tuple(origin)


def largest_piece(values):
    """Push everything but the biggest connected solid outside the surface.

    Works on the values alone, without redistancing, which is what a meshing
    script wants just before iso-surfacing.
    :func:`compas_vol.fabrication.keep_largest` is the same thing for a
    :class:`compas_vol.processes.Field`, and gives back a valid field.

    Parameters
    ----------
    values : array-like
        A sampled field, negative inside.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, int, float]
        The cleaned values, how many pieces were dropped, and the share of
        the material they held.

    Examples
    --------
    >>> import numpy as np
    >>> from compas_vol.fabrication import largest_piece
    >>> x, y, z = np.ogrid[-10:10:41j, -10:10:41j, -10:10:41j]
    >>> pair = np.minimum(np.sqrt((x - 5)**2 + y**2 + z**2) - 3.0, np.sqrt((x + 5)**2 + y**2 + z**2) - 1.0)
    >>> cleaned, dropped, share = largest_piece(pair)
    >>> dropped, round(share, 2)
    (1, 0.03)
    """
    ndimage = require("scipy.ndimage")

    values = np.array(values, dtype=float)
    inside = values < 0
    labels, count = ndimage.label(inside, structure=face_connectivity())
    if count <= 1:
        return values, 0, 0.0

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    loose = inside & (labels != sizes.argmax())
    values[loose] = np.abs(values[loose]) + 1e-3
    return values, int(count - 1), float((sizes.sum() - sizes.max()) / sizes.sum())
