from compas_vol.base import VolObject
from compas_vol.base import format_number


class Factor(VolObject):
    """Scale the scalar field of a volumetric object by a constant.

    The zero level set is unchanged for any non-zero ``f``, but the field's
    slope is scaled, which affects anything downstream that reads distances
    rather than just their sign.

    Parameters
    ----------
    o : :class:`compas_vol.base.VolObject`
        The input object.
    f : float
        The scale factor. Default is ``1.0``.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import Factor
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> round(Factor(vb, 2.0).get_distance([0, 0, 0]), 6)
    -10.0
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
        return "Factor({0!r},{1})".format(self.o, format_number(self.f))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return self.f * self.o.get_distance(point)

    def get_distance_numpy(self, x, y, z):
        return self.f * self.o.get_distance_numpy(x, y, z)
