from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number


class Overlay(VolObject):
    """Add a scaled copy of one object's field on top of another's.

    Useful for perturbing a base shape with a texture or microstructure at a
    small amplitude ``f``.

    Parameters
    ----------
    a : :class:`compas_vol.base.VolObject`
        The base object.
    b : :class:`compas_vol.base.VolObject`
        The object to overlay.
    f : float
        The amplitude of the overlay. Default is ``0.1``.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.modifications import Overlay
    >>> vs = VolSphere(Sphere(7, point=Point(2, 3, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> f = Overlay(vs, vb, 0.2)
    >>> isinstance(f.get_distance([0, 0, 0]), float)
    True
    """

    def __init__(self, a=None, b=None, f=0.1, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b
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

    def __repr__(self):
        return "Overlay({0!r},{1!r},{2})".format(self.a, self.b, format_number(self.f))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return self.a.get_distance(point) + self.f * self.b.get_distance(point)

    def get_distance_numpy(self, x, y, z):
        da, db = broadcast_distances(
            [self.a.get_distance_numpy(x, y, z), self.b.get_distance_numpy(x, y, z)], x, y, z
        )
        return da + self.f * db
