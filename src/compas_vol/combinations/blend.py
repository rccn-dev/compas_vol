from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number

#: Blend with a straight linear ramp.
LINEAR = 0
#: Blend with a quadratic ease-in/ease-out ramp.
QUADRATIC = 1


class Blend(VolObject):
    """A blend between two volumetric objects, controlled by a third.

    Where the control object ``c`` is deeply inside, ``a`` is returned; where
    it is far outside, ``b`` is returned. Across the band of width ``r``
    straddling its surface, the two are interpolated.

    Parameters
    ----------
    a, b : :class:`compas_vol.base.VolObject`
        The objects to blend between.
    c : :class:`compas_vol.base.VolObject`
        The control object driving the blend.
    r : float
        The width of the transition band. Default is ``1.0``.
    t : int
        The interpolation ramp: :data:`LINEAR` (``0``) or :data:`QUADRATIC` (``1``).

    Examples
    --------
    >>> from compas.geometry import Box, Plane, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolPlane, VolSphere
    >>> from compas_vol.combinations import Blend
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> vp = VolPlane(Plane([0, 0, 0], [0, 0, 1]))
    >>> bl = Blend(vs, vb, vp, 5.0)
    >>> isinstance(bl.get_distance([0, 0, 0]), float)
    True
    """

    def __init__(self, a=None, b=None, c=None, r=1.0, t=LINEAR, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b
        self.c = c
        self.r = r
        self._t = None
        self.t = t

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.a, "b": self.b, "c": self.c, "r": self.r, "t": self.t}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["b"], data["c"], data["r"], data["t"])

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def t(self):
        return self._t

    @t.setter
    def t(self, t):
        # The old implementation silently fell through and returned None for
        # any t other than 0 or 1.
        if t not in (LINEAR, QUADRATIC):
            raise ValueError("t must be LINEAR (0) or QUADRATIC (1), got {!r}".format(t))
        self._t = t

    def __repr__(self):
        return "Blend({0!r},{1!r},{2!r},{3},{4})".format(
            self.a, self.b, self.c, format_number(self.r), self.t
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        dc = self.c.get_distance(point)
        if dc < -self.r / 2:
            return self.a.get_distance(point)
        if dc > self.r / 2:
            return self.b.get_distance(point)

        da = self.a.get_distance(point)
        db = self.b.get_distance(point)
        f = dc / self.r + 0.5
        if self.t == QUADRATIC:
            f = 2 * f**2 if f < 0.5 else 1 - pow(-2 * f + 2, 2) / 2
        return (1 - f) * da + f * db

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        da, db, dc = broadcast_distances(
            [
                self.a.get_distance_numpy(x, y, z),
                self.b.get_distance_numpy(x, y, z),
                self.c.get_distance_numpy(x, y, z),
            ],
            x,
            y,
            z,
        )

        f = dc / self.r + 0.5
        if self.t == QUADRATIC:
            f = np.where(f < 0.5, 2 * f**2, 1 - ((-2 * f + 2) ** 2) / 2)
        blended = (1 - f) * da + f * db

        return np.where(dc < -self.r / 2, da, np.where(dc > self.r / 2, db, blended))
