from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number


class Morph(VolObject):
    """A linear interpolation between two volumetric objects.

    Parameters
    ----------
    a : :class:`compas_vol.base.VolObject`
        The object to morph from.
    b : :class:`compas_vol.base.VolObject`
        The object to morph to.
    f : float
        Interpolation factor, clamped to ``[0, 1]``. At ``f = 0`` object ``a``
        is returned, at ``f = 1`` object ``b``. Default is ``0.5``.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.combinations import Morph
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> m = Morph(vs, vb, 0.5)
    >>> m.get_distance([0, 0, 0]) < 0
    True
    """

    def __init__(self, a=None, b=None, f=0.5, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b
        self._f = None
        self.f = f

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.a, "b": self.b, "f": self.f}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["b"], data["f"])

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def f(self):
        return self._f

    @f.setter
    def f(self, f):
        self._f = max(min(float(f), 1.0), 0.0)

    def __repr__(self):
        return "Morph({0!r},{1!r},{2})".format(self.a, self.b, format_number(self.f))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        da = self.a.get_distance(point)
        db = self.b.get_distance(point)
        return (1.0 - self.f) * da + self.f * db

    def get_distance_numpy(self, x, y, z):
        da, db = broadcast_distances(
            [self.a.get_distance_numpy(x, y, z), self.b.get_distance_numpy(x, y, z)], x, y, z
        )
        return (1.0 - self.f) * da + self.f * db
