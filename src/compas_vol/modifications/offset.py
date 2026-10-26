from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number


class Offset(VolObject):
    """Grow or shrink an object by a distance, which may vary through space.

    ``distance`` is in model units: positive grows the solid outward, negative
    shrinks it. Given a volumetric object instead of a number, the offset is
    read from that object's field at each point, which is how one shape can
    be thickened more in one place than another -- an opening that flares
    towards both faces of a slab, a wall that thins with height. A
    :class:`Remap` is the usual driver, since it turns any distance into a
    dimension.

    The result is a distance field wherever the original was and the offset
    is constant; where the offset varies, it is a close estimate that keeps
    its zero level set exact.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to offset.
    distance : float | :class:`compas_vol.base.VolObject`
        The offset, in model units, or a field giving it per point.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.modifications import Offset
    >>> ball = VolSphere(Sphere(5, point=Point(0, 0, 0)))
    >>> round(Offset(ball, 2.0).get_distance([8, 0, 0]), 6)
    1.0
    >>> round(Offset(ball, -2.0).get_distance([0, 0, 0]), 6)
    -3.0
    """

    def __init__(self, obj=None, distance=0.0, name=None):
        super().__init__(name=name)
        self.o = obj
        self.distance = distance if isinstance(distance, VolObject) else float(distance)

    @property
    def __data__(self):
        return {"obj": self.o, "distance": self.distance}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], data["distance"])

    def __repr__(self):
        distance = repr(self.distance) if isinstance(self.distance, VolObject) else format_number(self.distance)
        return "Offset({!r},{})".format(self.o, distance)

    def get_distance(self, point):
        if isinstance(self.distance, VolObject):
            return self.o.get_distance(point) - self.distance.get_distance(point)
        return self.o.get_distance(point) - self.distance

    def get_distance_numpy(self, x, y, z):
        if isinstance(self.distance, VolObject):
            d, amount = broadcast_distances(
                [self.o.get_distance_numpy(x, y, z), self.distance.get_distance_numpy(x, y, z)], x, y, z
            )
            return d - amount
        return self.o.get_distance_numpy(x, y, z) - self.distance
