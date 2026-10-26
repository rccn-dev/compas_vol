"""Speed terms: what a process does at each point of the surface.

A process moves the surface along its normal at some speed. Erosion is a
positive speed (the surface retreats into the solid), growth a negative one.
Everything interesting is in how that speed varies across the surface, and
these terms are the pieces it is built from.

Two kinds, which is what keeps the algebra honest:

* **rates**, in millimetres per step: :class:`Uniform`;
* **signals**, dimensionless, usually in ``[-1, 1]`` or ``[0, 1]``:
  :class:`Curvature`, :class:`Convexity`, :class:`Concavity`,
  :class:`Shelter`, :class:`Values`.

Multiply a rate by signals to shape it, add rates together to combine them::

    speed = Uniform(0.25) * (1.0 + 0.8 * Convexity(length=9.0))
"""

import numpy as np

from compas_vol.runtime import require

__all__ = [
    "Term",
    "Uniform",
    "Smooth",
    "Curvature",
    "Convexity",
    "Concavity",
    "Shelter",
    "Values",
    "curvature_of",
    "gradient_magnitude_of",
]


def gradient_magnitude_of(field):
    """:class:`numpy.ndarray`: ``|grad phi|``, 1 everywhere for a true distance field."""
    gradients = np.gradient(field.values, *field.spacing)
    return np.sqrt(sum(g * g for g in gradients))


def curvature_of(field):
    """:class:`numpy.ndarray`: Mean curvature of the level sets, in 1/mm.

    The divergence of the unit gradient. Positive where the solid is convex
    (a sphere of radius R reads ``2/R``), negative in a hollow.
    """
    gradients = np.gradient(field.values, *field.spacing)
    magnitude = np.maximum(np.sqrt(sum(g * g for g in gradients)), 1e-9)
    return sum(np.gradient(g / magnitude, field.spacing[axis], axis=axis) for axis, g in enumerate(gradients))


class Term:
    """A speed term: something that produces an array from a field.

    Terms compose with ``+``, ``-`` and ``*``, with each other or with plain
    numbers, so a process can be written as an expression instead of a
    function.
    """

    def __call__(self, field):  # pragma: no cover - interface
        raise NotImplementedError

    def __add__(self, other):
        return _Combined(self, other, np.add, "+")

    __radd__ = __add__

    def __sub__(self, other):
        return _Combined(self, other, np.subtract, "-")

    def __rsub__(self, other):
        return _Combined(other, self, np.subtract, "-")

    def __mul__(self, other):
        return _Combined(self, other, np.multiply, "*")

    __rmul__ = __mul__

    def __neg__(self):
        return _Combined(0.0, self, np.subtract, "-")


def evaluate(term, field):
    """Evaluate a term, a number, or an array against a field."""
    if isinstance(term, Term):
        return term(field)
    if callable(term):
        return term(field)
    return np.asarray(term, dtype=float)


class _Combined(Term):
    def __init__(self, left, right, operation, symbol):
        self.left, self.right, self.operation, self.symbol = left, right, operation, symbol

    def __call__(self, field):
        return self.operation(evaluate(self.left, field), evaluate(self.right, field))

    def __repr__(self):
        return "({!r} {} {!r})".format(self.left, self.symbol, self.right)


class Uniform(Term):
    """The same speed everywhere, in millimetres per step.

    Parameters
    ----------
    rate : float
        Positive erodes, negative grows.
    """

    def __init__(self, rate=1.0):
        self.rate = float(rate)

    def __call__(self, field):
        return np.full(field.shape, self.rate)

    def __repr__(self):
        return "Uniform({})".format(self.rate)


class Curvature(Term):
    """Mean curvature, measured against a length, clipped to ``+-limit``.

    Curvature has units of 1/length, so it only means something next to a
    length: the size of the feature you care about. Measured against the voxel
    size instead -- an easy mistake -- every term becomes negligible and every
    process comes out as a smooth blob.

    Parameters
    ----------
    length : float
        The feature size curvature is compared against, in mm.
    limit : float
        Clip, so that a sharp corner cannot take an unbounded step.
    """

    def __init__(self, length=10.0, limit=3.0):
        self.length = float(length)
        self.limit = float(limit)

    def __call__(self, field):
        return np.clip(curvature_of(field) * self.length, -self.limit, self.limit)

    def __repr__(self):
        return "Curvature(length={}, limit={})".format(self.length, self.limit)


class Convexity(Curvature):
    """Curvature keeping only the convex side, in ``[0, 1]``.

    Edges and tips read 1, flats and hollows 0. Abrasion follows this: the
    parts that stick out meet whatever is doing the wearing.
    """

    def __call__(self, field):
        return np.clip(curvature_of(field) * self.length, 0.0, 1.0)


class Concavity(Curvature):
    """Curvature keeping only the concave side, in ``[0, 1]``.

    Hollows read 1. Chemical and salt weathering follow this, because that is
    where moisture stays -- and because a hollow that deepens becomes more
    concave, it is a feedback, which is what makes pitting run away into
    honeycomb.
    """

    def __call__(self, field):
        return np.clip(-curvature_of(field) * self.length, 0.0, 1.0)


class Shelter(Term):
    """How enclosed a point is, in ``[0, 1]``.

    Measured by blurring the solid over ``reach`` millimetres: a point whose
    surroundings are mostly rock is sheltered, one on an exposed nose is not.
    A flat face sits at 0. Cheaper than casting rays for occlusion, and for
    driving a weathering rate the difference does not show.

    Parameters
    ----------
    reach : float
        How far around each point to look, in mm.
    sharpness : float
        Contrast applied to the blurred value.
    """

    def __init__(self, reach=6.0, sharpness=2.5):
        self.reach = float(reach)
        self.sharpness = float(sharpness)

    def __call__(self, field):
        ndimage = require("scipy.ndimage")

        occlusion = ndimage.gaussian_filter((field.values < 0).astype(float), self.reach / field.voxel)
        return np.clip((occlusion - 0.5) * self.sharpness, 0.0, 1.0)

    def __repr__(self):
        return "Shelter(reach={}, sharpness={})".format(self.reach, self.sharpness)


class Smooth(Term):
    """Blur another term over a length, in mm.

    What it does for a growth process is set the finest thing that process can
    make. An instability -- growth that runs faster where the surface already
    bulges -- amplifies every wavelength, including the one-voxel wavelength,
    unless something removes the short end. Blurring the speed is that
    something, and the length you blur over comes out as the width of the
    folds or fingers.

    Parameters
    ----------
    term : :class:`Term` | callable | float | array
        What to smooth.
    length : float
        Blur radius, in mm.
    """

    def __init__(self, term, length=5.0):
        self.term = term
        self.length = float(length)

    def __call__(self, field):
        ndimage = require("scipy.ndimage")

        values = evaluate(self.term, field)
        if np.ndim(values) == 0:
            return values
        return ndimage.gaussian_filter(values, self.length / (2.0 * field.voxel))

    def __repr__(self):
        return "Smooth({!r}, length={})".format(self.term, self.length)


class Values(Term):
    """An array used directly as a signal: a hardness map, a noise field, a mask.

    Parameters
    ----------
    values : array-like
        Same shape as the field it will be evaluated against.
    """

    def __init__(self, values):
        self.values = np.asarray(values, dtype=float)

    def __call__(self, field):
        if self.values.shape not in (field.shape, ()):
            raise ValueError(
                "This signal is shaped {} but the field is {}.".format(self.values.shape, field.shape)
            )
        return self.values

    def __repr__(self):
        return "Values({})".format("x".join(str(n) for n in self.values.shape))
