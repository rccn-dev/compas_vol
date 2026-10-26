"""The sampled field that every process reads and writes."""

import numpy as np

from compas_vol.meshing import normalize_bounds
from compas_vol.meshing import sample
from compas_vol.runtime import require

__all__ = ["Field", "redistance", "lattice"]


def redistance(values, spacing):
    """Rebuild a signed distance field from its own zero level set.

    Every process moves the surface by an amount that varies in space, and
    that destroys the property a distance field is defined by, ``|grad phi| =
    1``. Everything downstream depends on it: a shell of 2 mm is only 2 mm
    thick if the field measures millimetres. So each step ends here.

    Fast marching is used rather than a distance transform of the thresholded
    solid, which would quantise the surface to whole voxels and leave visible
    terracing, and rather than dividing by the gradient magnitude, which is
    unstable: in testing it amplified its own noise until the model vanished.

    Parameters
    ----------
    values : :class:`numpy.ndarray`
        The field, negative inside.
    spacing : sequence[float]
        Voxel size along each axis.

    Returns
    -------
    :class:`numpy.ndarray`

    Raises
    ------
    ImportError
        If scikit-fmm is not installed. It is the ``processes`` extra:
        ``pip install compas-vol[processes]``.
    ValueError
        If the field has no zero crossing, so there is no surface to measure
        from -- usually a model that has been eroded away completely, or
        bounds that do not contain it.
    """
    skfmm = require("skfmm")

    values = np.asarray(values, dtype=float)
    if not (values.min() < 0 < values.max()):
        raise ValueError(
            "The field has no surface left: values run from {:.3f} to {:.3f}, all one sign. "
            "Erosion may have consumed the model, or the bounds may not contain it.".format(
                values.min(), values.max()
            )
        )
    return skfmm.distance(values, dx=list(spacing))


def lattice(bounds, voxel):
    """Grow bounds outward onto a world lattice of spacing ``voxel``.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
    voxel : float

    Returns
    -------
    tuple[tuple[float, ...], tuple[int, int, int]]
        The snapped bounds, and the sample count along each axis.

    Examples
    --------
    >>> lattice((0.5, 0, 0, 10, 4, 3.1), 2.0)
    ((0.0, 0.0, 0.0, 10.0, 4.0, 4.0), (6, 3, 3))
    """
    voxel = float(voxel)
    if voxel <= 0:
        raise ValueError("voxel must be positive, got {}.".format(voxel))
    x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
    low = [np.floor(v / voxel + 1e-9) * voxel for v in (x0, y0, z0)]
    high = [np.ceil(v / voxel - 1e-9) * voxel for v in (x1, y1, z1)]
    counts = tuple(max(2, int(round((h - lo) / voxel)) + 1) for lo, h in zip(low, high))
    high = [lo + (n - 1) * voxel for lo, n in zip(low, counts)]
    return tuple(float(v) for v in low + high), counts


class Field:
    """A distance field on a regular grid, with the grid it lives on.

    Processes are grid-native: erosion, growth and phase separation are all
    iterations over samples, not closed-form expressions. This carries the
    three things they all need -- the values, where the grid starts, and how
    big a voxel is -- plus the record of what has been done to it.

    Everything is in model units (millimetres, by convention here), including
    the lengths that curvature and shelter are measured against.

    Parameters
    ----------
    values : :class:`numpy.ndarray`
        Signed distances on the grid, negative inside the solid.
    origin : tuple[float, float, float]
        World coordinates of ``values[0, 0, 0]``.
    spacing : tuple[float, float, float]
        Voxel size along each axis.
    history : list[dict], optional
        What produced this field. Carried forward by every operation, so a
        result can say how it was made.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.processes import Field
    >>> field = Field.from_object(VolSphere(Sphere(20, point=Point(0, 0, 0))), bounds=30.0, resolution=48)
    >>> field.shape
    (48, 48, 48)
    >>> round(field.voxel, 3)
    1.277
    """

    def __init__(self, values, origin, spacing, history=None):
        self.values = np.asarray(values, dtype=float)
        if self.values.ndim != 3:
            raise ValueError("A field is a 3D grid; got an array of shape {}.".format(self.values.shape))
        self.origin = tuple(float(v) for v in origin)
        self.spacing = tuple(float(v) for v in spacing)
        self.history = list(history or [])
        # Constraints, set by `constrain` and carried by `copy`. Sampled once,
        # onto this grid, so applying them costs a min and a max per step.
        self.keep = None
        self.within = None
        self.margin = 0.0

    # ==========================================================================
    # construction
    # ==========================================================================

    @classmethod
    def from_object(cls, obj, bounds, resolution=128, workers=None, redistanced=True, voxel=None):
        """Sample a volumetric object onto a grid.

        Parameters
        ----------
        obj : :class:`compas_vol.base.VolObject`
            What to sample.
        bounds : :class:`compas.geometry.Box` | float | sequence
            The domain. See :func:`compas_vol.meshing.normalize_bounds`. Leave
            room around the model: a process that grows outward has nowhere to
            go otherwise, and anything touching the edge is cut there.
        resolution : int | tuple[int, int, int]
            Samples along each axis. This is the resolution the *process* runs
            at, and it sets the finest feature any of them can produce: below
            about two voxels, nothing survives.
        workers : int, optional
            Threads used for sampling. See :func:`compas_vol.meshing.sample`.
        redistanced : bool
            Rebuild the distance field after sampling. Most volumetric objects
            are not metric (a TPMS field, anything blended or multiplied), and
            processes need a true distance field to measure millimetres with.
        voxel : float, optional
            Sample on a world lattice of this spacing instead of at
            ``resolution``: the bounds grow outward to the nearest lattice
            planes, and every sample sits on a multiple of ``voxel``. Two
            fields sampled this way over overlapping boxes share their samples
            exactly, which is what lets a model built piece by piece agree
            with itself where the pieces meet.

        Returns
        -------
        :class:`Field`

        Examples
        --------
        >>> from compas.geometry import Point, Sphere
        >>> from compas_vol.primitives import VolSphere
        >>> ball = VolSphere(Sphere(10, point=Point(0, 0, 0)))
        >>> field = Field.from_object(ball, (-12.3, -12, -12, 12, 12, 12), voxel=2.0, redistanced=False)
        >>> field.origin, field.spacing, field.shape
        ((-14.0, -12.0, -12.0), (2.0, 2.0, 2.0), (14, 13, 13))
        """
        if voxel is not None:
            bounds, resolution = lattice(bounds, voxel)
        values, origin, spacing = sample(obj, bounds, resolution, workers=workers)
        field = cls(values, origin, spacing)
        field.record("sample", source=repr(obj), bounds=normalize_bounds(bounds), resolution=field.shape)
        return field.redistanced() if redistanced else field

    @classmethod
    def empty(cls, bounds, resolution=128, fill=1.0):
        """An unset grid over a domain, for generators that build their own field."""
        x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
        counts = (resolution,) * 3 if isinstance(resolution, (int, float)) else tuple(int(v) for v in resolution)
        spacing = tuple((hi - lo) / (n - 1) for lo, hi, n in zip((x0, y0, z0), (x1, y1, z1), counts))
        return cls(np.full(counts, float(fill)), (x0, y0, z0), spacing)

    # ==========================================================================
    # properties
    # ==========================================================================

    @property
    def shape(self):
        """tuple[int, int, int]: Samples along each axis."""
        return self.values.shape

    @property
    def voxel(self):
        """float: The smallest voxel dimension, which limits every feature size."""
        return min(self.spacing)

    @property
    def bounds(self):
        """tuple: ``(xmin, ymin, zmin, xmax, ymax, zmax)`` of the sampled domain."""
        return self.origin + tuple(o + (n - 1) * s for o, n, s in zip(self.origin, self.shape, self.spacing))

    def coordinates(self):
        """tuple[:class:`numpy.ndarray`, ...]: World coordinates as broadcastable axes."""
        return tuple(
            (o + np.arange(n) * s).reshape([-1 if i == axis else 1 for i in range(3)])
            for axis, (o, n, s) in enumerate(zip(self.origin, self.shape, self.spacing))
        )

    def solid_fraction(self):
        """float: Share of the sampled box that is inside the solid."""
        return float((self.values < 0).mean())

    # ==========================================================================
    # operations
    # ==========================================================================

    def copy(self, values=None):
        """A copy, optionally with different values but the same grid, history and constraints."""
        field = Field(self.values if values is None else values, self.origin, self.spacing, self.history)
        field.keep, field.within, field.margin = self.keep, self.within, self.margin
        return field

    def redistanced(self):
        """A copy whose values are a true signed distance field again.

        Also where a field's constraints are imposed (see :meth:`constrain`).
        Every process ends its steps here, which is what lets a constraint
        hold through all of them without any of them knowing it exists.
        """
        values = redistance(self._imposed(self.values), self.spacing)
        return self.copy(self._imposed(values))

    # ==========================================================================
    # constraints
    # ==========================================================================

    def constrain(self, keep=None, within=None, margin=0.0):
        """A copy that no process can take ``keep`` away from, or grow beyond ``within``.

        A beam in an eroded slab, the floor under a planter, a bearing face
        that has to stay flat: the parts of a design that are not negotiable,
        however the process around them runs. The constraint is imposed every
        time the field is redistanced -- which every process does after every
        step -- so it holds through erosion, pitting, jointing and opening
        alike, and through whatever runs after them, without any of them
        taking a parameter for it.

        It is a guarantee, not a preference: the solid always contains
        ``keep`` and never leaves ``within``, to within the half voxel that
        redistancing moves a surface. :meth:`violation` measures it.

        Parameters
        ----------
        keep : :class:`compas_vol.base.VolObject` | array-like, optional
            Solid that must remain. Material is never removed from it.
        within : :class:`compas_vol.base.VolObject` | array-like, optional
            The envelope. Growth never adds material outside it.
        margin : float
            Distance, in mm, over which a process slows down as it approaches
            a constraint, so that it fades into the kept solid rather than
            stopping dead against it. ``0`` leaves the process at full speed
            right up to the constraint, which then shows as a crisp edge --
            the right look for a cut, the wrong one for a weathered beam.

        Returns
        -------
        :class:`Field`

        Examples
        --------
        >>> from compas.geometry import Box, Frame
        >>> from compas_vol.primitives import VolBox
        >>> from compas_vol.processes import Field, abrasion
        >>> slab = VolBox(Box(40, 40, 10), 0.0)
        >>> beam = VolBox(Box(8, 40, 10, frame=Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))), 0.0)
        >>> field = Field.from_object(slab, bounds=26.0, resolution=40).constrain(keep=beam)
        >>> worn = abrasion(field, depth=6.0, edge_bias=0.0)
        >>> round(float(worn.solid_fraction() - field.solid_fraction()), 2) < 0   # the slab wore away
        True
        >>> worn.violation()["keep"] < worn.voxel                                 # the beam did not
        True
        """
        constrained = self.copy()
        if keep is not None:
            constrained.keep = self._on_grid(keep)
        if within is not None:
            constrained.within = self._on_grid(within)
        constrained.margin = float(margin)
        constrained = constrained.copy(constrained._imposed(constrained.values))
        if constrained.values.min() < 0 < constrained.values.max():
            constrained = constrained.redistanced()
        return constrained.record(
            "constrain",
            keep=_describe(keep),
            within=_describe(within),
            margin=float(margin),
        )

    def violation(self):
        """How far the solid strays from its constraints, in mm.

        Returns
        -------
        dict
            ``keep``: the deepest point of ``keep`` that is not solid, as a
            distance into ``keep`` (``0`` when it is all there). ``within``:
            the furthest solid point outside ``within``. Either is ``0`` for a
            constraint that is not set. Anything under a voxel is the grid's
            resolution, not a breach.
        """
        result = {"keep": 0.0, "within": 0.0}
        if self.keep is not None:
            lost = (self.values > 0) & (self.keep < 0)
            result["keep"] = float(-self.keep[lost].min()) if lost.any() else 0.0
        if self.within is not None:
            outside = (self.values < 0) & (self.within > 0)
            result["within"] = float(self.within[outside].max()) if outside.any() else 0.0
        return result

    def falloff(self, rate):
        """Scale a speed down as it nears a constraint.

        Erosion (a positive rate) fades to nothing at ``keep``; growth (a
        negative rate) fades to nothing at the edge of ``within``. Used by
        :func:`compas_vol.processes.evolve` and :meth:`displaced`, so every
        process slows near a constraint rather than running into it.

        Parameters
        ----------
        rate : :class:`numpy.ndarray` | float
            Millimetres per step, per point.

        Returns
        -------
        :class:`numpy.ndarray`
        """
        rate = np.asarray(rate, dtype=float)
        if self.margin <= 0 or (self.keep is None and self.within is None):
            return rate
        result = np.broadcast_to(rate, np.broadcast_shapes(rate.shape, self.shape)).copy()
        if self.keep is not None:
            eroding = result > 0
            result[eroding] *= _smoothstep(self.keep / self.margin)[eroding]
        if self.within is not None:
            growing = result < 0
            result[growing] *= _smoothstep(-self.within / self.margin)[growing]
        return result

    def _imposed(self, values):
        """``values`` with the constraints applied: union with keep, intersection with within."""
        if self.keep is not None:
            values = np.minimum(values, self.keep)
        if self.within is not None:
            values = np.maximum(values, self.within)
        return values

    def _on_grid(self, constraint):
        """A constraint as an array on this grid, sampling it if it is an object."""
        from compas_vol.base import VolObject

        if isinstance(constraint, VolObject):
            values = np.asarray(constraint.get_distance_numpy(*self.coordinates()), dtype=float)
            return np.broadcast_to(values, self.shape).copy()
        values = np.asarray(constraint, dtype=float)
        if values.shape != self.shape:
            raise ValueError("A constraint is shaped {} but the field is {}.".format(values.shape, self.shape))
        return values

    def cropped(self, bounds):
        """The part of the field inside ``bounds``, on the same samples.

        Nothing is resampled: the result is a slice of this grid, so two
        neighbouring crops of one field agree exactly where they meet.

        Parameters
        ----------
        bounds : sequence[float]
            ``(xmin, ymin, zmin, xmax, ymax, zmax)``. Rounded outward to whole
            samples, so the crop always covers it.

        Returns
        -------
        :class:`Field`

        Examples
        --------
        >>> import numpy as np
        >>> from compas_vol.processes import Field
        >>> field = Field(np.zeros((11, 11, 11)), (0, 0, 0), (1, 1, 1))
        >>> part = field.cropped((2, 2, 2, 4.5, 6, 6))
        >>> part.shape, part.origin
        ((4, 5, 5), (2.0, 2.0, 2.0))
        """
        x0, y0, z0, x1, y1, z1 = normalize_bounds(bounds)
        slices, origin = [], []
        for axis, (lo, hi) in enumerate(((x0, x1), (y0, y1), (z0, z1))):
            o, s, n = self.origin[axis], self.spacing[axis], self.shape[axis]
            start = max(0, int(np.floor((lo - o) / s + 1e-9)))
            stop = min(n, int(np.ceil((hi - o) / s - 1e-9)) + 1)
            if stop - start < 2:
                raise ValueError("The crop {} leaves fewer than two samples along axis {}.".format(bounds, axis))
            slices.append(slice(start, stop))
            origin.append(o + start * s)
        index = tuple(slices)
        part = Field(self.values[index], origin, self.spacing, self.history)
        part.keep = None if self.keep is None else self.keep[index]
        part.within = None if self.within is None else self.within[index]
        part.margin = self.margin
        return part

    def displaced(self, amount):
        """Move the surface outward-normal by ``amount`` mm, then redistance.

        Positive eats material, negative adds it, matching the sign of a speed
        in :func:`compas_vol.processes.evolve`, and like a speed it fades near
        the field's constraints (see :meth:`constrain`). Use it for one-shot changes --
        bedding, channels, joints -- where nothing has to be iterated.

        Parameters
        ----------
        amount : float | :class:`numpy.ndarray`
            Millimetres of retreat, per point or everywhere.

        Returns
        -------
        :class:`Field`
        """
        moved = self.copy(self.values + self.falloff(amount))
        return moved.redistanced()

    def record(self, operation, **parameters):
        """Note an operation in the field's history, for provenance."""
        self.history = self.history + [dict(operation=operation, **parameters)]
        return self

    def provenance(self):
        """str: The history as readable lines, for a methods section or a log."""
        lines = []
        for entry in self.history:
            arguments = ", ".join("{}={!r}".format(k, v) for k, v in entry.items() if k != "operation")
            lines.append("{}({})".format(entry["operation"], arguments))
        return "\n".join(lines)

    def to_volume(self, name=None):
        """Wrap as a :class:`compas_vol.primitives.VolGrid`, back in the CSG world.

        This is the bridge: once a process has run, its result models like any
        other volumetric object -- shell it, put a lattice inside it, subtract
        it, export it.

        Returns
        -------
        :class:`compas_vol.primitives.VolGrid`
        """
        from compas_vol.primitives import VolGrid

        grid = VolGrid(self.values, self.origin, self.spacing, name=name)
        grid.history = list(self.history)
        return grid

    def __repr__(self):
        return "Field({}x{}x{} @ {:.3f} mm)".format(*self.shape, self.voxel)


def _smoothstep(t):
    """0 below 0, 1 above 1, and a smooth S between."""
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _describe(constraint):
    """A constraint as a short string for the history."""
    if constraint is None:
        return None
    if isinstance(constraint, np.ndarray):
        return "array{}".format(constraint.shape)
    return repr(constraint)
