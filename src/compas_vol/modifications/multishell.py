from compas_vol.base import VolObject
from compas_vol.base import format_number


class MultiShell(VolObject):
    """A nested set of concentric shells offset from a volumetric object.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The input object.
    thickness : float
        The thickness of each shell.
    distance : float
        The spacing between successive shells.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import MultiShell
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> sh = MultiShell(vb, 1.0, 2.5)
    >>> isinstance(sh.get_distance([0, 0, 0]), float)
    True
    """

    def __init__(self, obj, thickness=1.0, distance=3.0, name=None):
        super().__init__(name=name)
        self.o = obj
        self.thickness = thickness
        self.distance = distance

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"obj": self.o, "thickness": self.thickness, "distance": self.distance}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], data["thickness"], data["distance"])

    def __repr__(self):
        return "MultiShell({0!r},{1},{2})".format(
            self.o, format_number(self.thickness), format_number(self.distance)
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        do = self.o.get_distance(point)
        remainder = do % self.distance
        return min(remainder, self.distance - remainder) - self.thickness / 2

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        do = self.o.get_distance_numpy(x, y, z)
        remainder = do % self.distance
        return np.minimum(remainder, self.distance - remainder) - self.thickness / 2
