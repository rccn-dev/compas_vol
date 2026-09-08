from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class Heart(VolObject):
    """A heart shape, defined by a size and a frame.

    Like :class:`VolEgg` this is a scalar field, not a metric distance field:
    the zero level set is the heart's surface, but the values away from it are
    not distances.

    Parameters
    ----------
    size : float
        Scale factor.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas.geometry import Frame
    >>> from compas_vol.primitives import Heart
    >>> heart = Heart(size=4, frame=Frame((1, 2, 3), (1, 0, 0), (0, 1, 0)))
    >>> heart.get_distance([1, 2, 3]) < 0
    True
    """

    def __init__(self, size=3.0, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.size = size
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"size": self.size, "frame": self.frame.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["size"], Frame.__from_data__(data["frame"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        self.inversetransform = inverse_matrix_from_frame(frame)

    def __repr__(self):
        return "Heart({0},{1!r})".format(format_number(self.size), self.frame)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        # The old single-point implementation ignored the frame entirely, so it
        # disagreed with the vectorized one for any non-world frame.
        p = self._as_point(point)
        p.transform(self.inversetransform)

        s = self.size * 0.43
        x, y, z = p.x / s, p.y / s, p.z / s
        return 320 * ((-(x**2) * z**3 - 9 * y**2 * z**3 / 80) + (x**2 + 9 * y**2 / 4 + z**2 - 1) ** 3)

    def get_distance_numpy(self, x, y, z):
        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        s = self.size * 0.43
        sx, sy, sz = xt / s, yt / s, zt / s
        return 320 * (
            (-(sx**2) * sz**3 - 9 * sy**2 * sz**3 / 80) + (sx**2 + 9 * sy**2 / 4 + sz**2 - 1) ** 3
        )
