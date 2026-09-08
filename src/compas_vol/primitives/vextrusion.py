from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import closest_point_on_polyline_xy
from compas.geometry import is_point_in_polygon_xy

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolExtrusion(VolObject):
    """A volumetric extrusion of a closed polyline along the local Z axis.

    The extrusion is centred on the frame, running from ``-height/2`` to
    ``+height/2``.

    Parameters
    ----------
    polyline : sequence[point]
        The base polyline, in the local XY plane. If the first and last points
        differ the polyline is closed implicitly.
    height : float
        The height of the extrusion.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.primitives import VolExtrusion
    >>> square = [(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0), (-5, -5, 0)]
    >>> ext = VolExtrusion(square, 10.0)
    >>> round(ext.get_distance([0, 0, 0]), 6)
    -5.0
    """

    def __init__(self, polyline, height=1.0, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.polyline = polyline
        self.height = height
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "polyline": [list(p) for p in self.polyline],
            "height": self.height,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["polyline"], data["height"], Frame.__from_data__(data["frame"]))

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

    @property
    def closed_polyline(self):
        """The base polyline, guaranteed to repeat its first point at the end."""
        pts = [tuple(p) for p in self.polyline]
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts

    def __repr__(self):
        return "VolExtrusion({0}, {1}, {2!r})".format(
            [tuple(p) for p in self.polyline], format_number(self.height), self.frame
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        tp = Point(p.x, p.y, 0)
        polyline = self.closed_polyline
        cp = closest_point_on_polyline_xy(tp, polyline)
        d = tp.distance_to_point(cp)
        if is_point_in_polygon_xy(tp, polyline):
            d = -d
        return max(d, abs(p.z) - self.height / 2.0)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)
        shape = np.broadcast_shapes(np.shape(xt), np.shape(yt))
        px = np.broadcast_to(xt, shape)
        py = np.broadcast_to(yt, shape)

        pts = self.closed_polyline

        # Standard 2D polygon SDF: the minimum squared distance to any edge,
        # signed by a crossing-number test. Looping over the edges keeps peak
        # memory at O(grid) instead of the O(grid * edges) of the previous
        # fully-tiled implementation.
        d2 = np.full(shape, np.inf)
        sign = np.ones(shape)

        for (ax, ay, *_), (bx, by, *_) in zip(pts[:-1], pts[1:]):
            ex, ey = bx - ax, by - ay
            wx, wy = px - ax, py - ay

            ee = ex * ex + ey * ey
            if ee == 0:
                continue
            h = np.clip((wx * ex + wy * ey) / ee, 0.0, 1.0)
            qx = wx - ex * h
            qy = wy - ey * h
            d2 = np.minimum(d2, qx * qx + qy * qy)

            c1 = py >= ay
            c2 = py < by
            c3 = ex * wy > ey * wx
            crossing = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
            sign = np.where(crossing, -sign, sign)

        dxy = sign * np.sqrt(d2)
        return np.maximum(dxy, np.abs(zt) - self.height / 2.0)
