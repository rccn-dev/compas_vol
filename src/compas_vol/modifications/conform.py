from compas_vol.base import VolObject
from compas_vol.base import format_number

__all__ = ["Conform"]


class Conform(VolObject):
    """Evaluate an object in a coordinate built from another object's field.

    A lattice tiles world space. It does not know a building is there, so a
    gyroid inside a curved shell is cut wherever the shell turns away from the
    grid: cells are sliced into slivers at the surface, and the wall thickness
    a designer asked for is not what gets built.

    This replaces one of the three coordinates a field is evaluated in with the
    *signed distance to a guide*. Every level of the guide -- its surface, and
    every offset inside and outside it -- becomes a level of the substituted
    axis. A pattern that used to repeat in flat Z now repeats in shells
    parallel to the guide, so it follows the skin of whatever the guide is: a
    sphere, an eroded rock, or a closed mesh baked with
    :meth:`compas_vol.primitives.VolGrid.from_mesh`.

    The classic use is a shell lattice. Take the guide's own shell for the
    region, and conform a TPMS into it: the cells then run parallel to the
    surface all the way round, and the layer count through the thickness is
    something you set rather than something you get.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The field to evaluate in the new coordinates -- usually a periodic one.
    guide : :class:`compas_vol.base.VolObject`
        Whose distance field replaces the axis. It should be metric, or the
        spacing of the resulting layers will not be in model units. Anything
        blended, multiplied, or a raw ``TPMS`` is not; primitives, booleans of
        them, and a redistanced :class:`compas_vol.processes.Field` are.
    axis : int
        Which coordinate to replace: 0 for x, 1 for y, 2 for z.
    scale : float
        Multiplies the guide's distance before it is substituted. Below 1 the
        layers spread out, above 1 they crowd together. With a TPMS of cell
        ``c``, a scale of ``c / t`` puts exactly one cell across a wall of
        thickness ``t``.
    offset : float
        Added after scaling, which slides the pattern through the thickness.

    Attributes
    ----------
    obj, guide : :class:`compas_vol.base.VolObject`
    axis : int
    scale, offset : float

    Notes
    -----
    **What this does not do.** Only the substituted axis follows the guide.
    The other two remain world coordinates, so cells stretch where the surface
    turns across them -- most visibly near a surface that runs parallel to the
    substituted axis, where the guide's distance barely changes. That is the
    honest limit of a one-coordinate substitution: a lattice that follows a
    surface in *all three* directions needs a global parametrization of the
    solid, which is a hex-meshing problem and not a field operation at all.

    In exchange it costs one extra field evaluation, works on any guide
    whatsoever, and cannot fail -- there is no parametrization to be singular.

    The result is not metric even when both inputs are: substituting a
    coordinate stretches the field. Shell it, and redistance before measuring
    a thickness from it.

    Examples
    --------
    >>> from compas.geometry import Sphere
    >>> from compas_vol.microstructures import TPMSSolid
    >>> from compas_vol.modifications import Conform
    >>> from compas_vol.primitives import VolSphere
    >>> gyroid = TPMSSolid("Gyroid", cell_size=10.0, thickness=2.0)
    >>> shell = Conform(gyroid, VolSphere(Sphere(20.0)), axis=2)
    >>> round(shell.get_distance([0, 0, 20]), 6) == round(gyroid.get_distance([0, 0, 0]), 6)
    True

    Anywhere on the guide's surface the substituted axis reads zero, so the
    top of the sphere and the bottom of it see the same slice of the pattern
    -- 40 mm apart in world Z, and at the same place in the lattice:

    >>> round(shell.get_distance([0, 0, -20]), 6) == round(shell.get_distance([0, 0, 20]), 6)
    True

    And 5 mm inside the surface, both read the same slice as each other again,
    which is what "the lattice follows the skin" means:

    >>> round(shell.get_distance([0, 0, 15]), 6) == round(shell.get_distance([0, 0, -15]), 6)
    True
    """

    def __init__(self, obj=None, guide=None, axis=2, scale=1.0, offset=0.0, name=None):
        super().__init__(name=name)
        self._axis = None
        self.obj = obj
        self.guide = guide
        self.axis = axis
        self.scale = scale
        self.offset = offset

    # ==========================================================================
    # properties
    # ==========================================================================

    @property
    def axis(self):
        """int: The coordinate replaced by the guide's distance."""
        return self._axis

    @axis.setter
    def axis(self, axis):
        axis = int(axis)
        if axis not in (0, 1, 2):
            raise ValueError("axis must be 0, 1 or 2; got {}.".format(axis))
        self._axis = axis

    @property
    def __data__(self):
        return {
            "obj": self.obj,
            "guide": self.guide,
            "axis": self.axis,
            "scale": self.scale,
            "offset": self.offset,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], data["guide"], data["axis"], data["scale"], data["offset"])

    def __repr__(self):
        return "Conform({!r}, {!r}, {}, {}, {})".format(
            self.obj, self.guide, self.axis, format_number(self.scale), format_number(self.offset)
        )

    # ==========================================================================
    # distance
    # ==========================================================================

    def get_distance(self, point):
        """Distance at a single point.

        Parameters
        ----------
        point : sequence[float]

        Returns
        -------
        float
        """
        coordinates = list(self._as_point(point))
        coordinates[self.axis] = self.scale * self.guide.get_distance(point) + self.offset
        return self.obj.get_distance(coordinates)

    def get_distance_numpy(self, x, y, z):
        """Distance for an ogrid of points.

        Parameters
        ----------
        x, y, z : :class:`numpy.ndarray`

        Returns
        -------
        :class:`numpy.ndarray`
        """
        import numpy as np

        distance = self.scale * self.guide.get_distance_numpy(x, y, z) + self.offset

        # The guide's field is a full grid, so the substituted coordinate is no
        # longer an ogrid axis. The other two have to be broadcast up to match
        # it, or the child sees three arrays that no longer describe one point.
        coordinates = [x, y, z]
        coordinates[self.axis] = distance
        shape = np.broadcast_shapes(*(np.shape(c) for c in coordinates))
        return self.obj.get_distance_numpy(*(np.broadcast_to(c, shape) for c in coordinates))
