from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances


class Division(VolObject):
    """The quotient of the scalar fields of two volumetric objects.

    Like :class:`Addition`, the result is a scalar field rather than a metric
    distance field. Note that the quotient is undefined on the zero level set
    of ``b``; the vectorized version yields ``inf`` or ``nan`` there.

    Parameters
    ----------
    a : :class:`compas_vol.base.VolObject`
        The numerator object.
    b : :class:`compas_vol.base.VolObject`
        The denominator object.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.combinations import Division
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> d = Division(vs, vb)
    >>> isinstance(d.get_distance([0, 0, 0]), float)
    True
    """

    def __init__(self, a=None, b=None, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.a, "b": self.b}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["b"])

    def __repr__(self):
        # The old implementation referenced ``self.objs``, which this class
        # never defined, so repr() raised AttributeError.
        return "Division({0!r},{1!r})".format(self.a, self.b)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return self.a.get_distance(point) / self.b.get_distance(point)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        da, db = broadcast_distances(
            [self.a.get_distance_numpy(x, y, z), self.b.get_distance_numpy(x, y, z)], x, y, z
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.divide(da, db)
