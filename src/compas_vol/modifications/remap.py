from compas_vol.base import VolObject
from compas_vol.base import format_number

#: Easing curves available to :class:`Remap`.
EASINGS = ["linear", "smooth"]


class Remap(VolObject):
    """Map the field of an object from one value range into another.

    This turns any volumetric object into a *driver*: a field whose value at
    each point is a design parameter rather than a distance. The distance to a
    sphere, remapped from ``(0, 40)`` to ``(2.5, 0.8)``, reads as "2.5 mm at
    the sphere, thinning to 0.8 mm 40 mm away", and can be passed wherever a
    parameter accepts a field, such as ``TPMSSolid(thickness=...)``.

    Values outside ``source`` are clamped, so the parameter never leaves
    ``target``. The zero level set of the result is generally meaningless;
    a remapped field is meant to drive another object, not to be meshed.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object whose field is remapped.
    source : tuple[float, float]
        The field values mapped to the start and end of ``target``.
    target : tuple[float, float]
        The output values. ``target[0]`` is returned at ``source[0]``.
    ease : {"linear", "smooth"}
        ``"smooth"`` applies a smoothstep, so the parameter eases in and out of
        its end values instead of changing slope abruptly at the clamps.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.modifications import Remap
    >>> attractor = VolSphere(Sphere(1, point=Point(0, 0, 0)))
    >>> thickness = Remap(attractor, source=(0, 20), target=(3.0, 1.0))
    >>> thickness.get_distance([11, 0, 0])
    2.0
    >>> thickness.get_distance([100, 0, 0])
    1.0
    """

    def __init__(self, obj=None, source=(0.0, 1.0), target=(0.0, 1.0), ease="linear", name=None):
        super().__init__(name=name)
        self._ease = None
        self._source = None
        self.o = obj
        self.source = source
        self.target = tuple(float(v) for v in target)
        self.ease = ease

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "obj": self.o,
            "source": list(self.source),
            "target": list(self.target),
            "ease": self.ease,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], tuple(data["source"]), tuple(data["target"]), data["ease"])

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, source):
        s0, s1 = (float(v) for v in source)
        if s0 == s1:
            raise ValueError("source must span a non-empty range, got {!r}".format(source))
        self._source = (s0, s1)

    @property
    def ease(self):
        return self._ease

    @ease.setter
    def ease(self, ease):
        if ease not in EASINGS:
            raise ValueError("ease must be one of {}, got {!r}".format(EASINGS, ease))
        self._ease = ease

    def __repr__(self):
        return "Remap({0!r},({1},{2}),({3},{4}),{5!r})".format(
            self.o,
            format_number(self.source[0]),
            format_number(self.source[1]),
            format_number(self.target[0]),
            format_number(self.target[1]),
            self.ease,
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def _remap(self, d):
        import numpy as np

        s0, s1 = self.source
        v0, v1 = self.target
        t = np.clip((d - s0) / (s1 - s0), 0.0, 1.0)
        if self.ease == "smooth":
            t = t * t * (3.0 - 2.0 * t)
        return v0 + t * (v1 - v0)

    def get_distance(self, point):
        return float(self._remap(self.o.get_distance(point)))

    def get_distance_numpy(self, x, y, z):
        return self._remap(self.o.get_distance_numpy(x, y, z))
