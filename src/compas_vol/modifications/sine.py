from math import sin

from compas_vol.base import VolObject
from compas_vol.base import format_number


class Sine(VolObject):
    """Apply a sine wave to the scalar field of a volumetric object.

    This turns a distance field into a periodic banded field, giving a set of
    nested surfaces at every multiple of the wavelength.

    The COMPAS 1 version assigned ``self.f = f`` with no such parameter in
    scope, so constructing it always raised :exc:`NameError`. ``f`` is now a
    real frequency argument.

    Parameters
    ----------
    o : :class:`compas_vol.base.VolObject`
        The input object.
    f : float
        The frequency of the wave. Default is ``1.0``.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import Sine
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> isinstance(Sine(vb).get_distance([0, 0, 0]), float)
    True
    """

    def __init__(self, o, f=1.0, name=None):
        super().__init__(name=name)
        self.o = o
        self.f = f

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"o": self.o, "f": self.f}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["o"], data["f"])

    def __repr__(self):
        return "Sine({0!r},{1})".format(self.o, format_number(self.f))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return sin(self.f * self.o.get_distance(point))

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        return np.sin(self.f * self.o.get_distance_numpy(x, y, z))
