from compas_vol.base import VolObject
from compas_vol.base import format_number


class Shell(VolObject):
    """Convert a solid volumetric object into a boundary shell of constant thickness.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The input object.
    thickness : float
        The thickness of the shell.
    side : float
        Side factor. At ``1.0`` the shell is offset to the inside, at ``0.5``
        half to either side of the original surface, at ``0.0`` to the outside.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import Shell
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> sh = Shell(vb, 2.5, 0.5)
    >>> sh.get_distance([0, 0, 0]) > 0
    True
    """

    def __init__(self, obj, thickness=1.0, side=0.0, name=None):
        super().__init__(name=name)
        self.o = obj
        self.thickness = thickness
        self.side = side

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"obj": self.o, "thickness": self.thickness, "side": self.side}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], data["thickness"], data["side"])

    def __repr__(self):
        return "Shell({0!r},{1},{2})".format(
            self.o, format_number(self.thickness), format_number(self.side)
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        do = self.o.get_distance(point)
        return abs(do + (self.side - 0.5) * self.thickness) - self.thickness / 2.0

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        do = self.o.get_distance_numpy(x, y, z)
        return np.abs(do + (self.side - 0.5) * self.thickness) - self.thickness / 2.0
