from math import pi

from compas_vol.base import VolObject

from .tpms import TPMSTYPES
from .tpms import resolve_tpmstype
from .tpms import tpms_field


class TPMSAttractor(VolObject):
    """A TPMS whose wavelength is driven by the distance to another object.

    Near the attractor the cells take the first of the two wavelengths, far
    from it the second, interpolating in between. This grades the density of
    the microstructure across a part.

    In COMPAS 1 this class was a partial copy of :class:`TPMS` supporting only
    two surface types, with the attractor logic left commented out as
    Rhino-specific code. It is implemented here against any volumetric object.

    Parameters
    ----------
    attractor : :class:`compas_vol.base.VolObject`
        The object whose distance field drives the wavelength.
    tpmstype : int | str
        The surface type. See :data:`compas_vol.microstructures.TPMSTYPES`.
    wavelength_range : tuple[float, float]
        The wavelengths at the near and far ends of ``distance_range``.
    distance_range : tuple[float, float]
        The distances from the attractor mapped to ``wavelength_range``.
        Distances outside this range are clamped.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.microstructures import TPMSAttractor
    >>> att = VolSphere(Sphere(5, point=Point(0, 0, 0)))
    >>> t = TPMSAttractor(att, 'Gyroid', (2.0, 8.0), (0.0, 20.0))
    >>> isinstance(t.get_distance([3, 4, 5]), float)
    True
    """

    def __init__(
        self,
        attractor=None,
        tpmstype=0,
        wavelength_range=(1.0, 5.0),
        distance_range=(0.0, 10.0),
        name=None,
    ):
        super().__init__(name=name)
        self._tpmstype = None
        self.attractor = attractor
        self.tpmstype = tpmstype
        self.wavelength_range = tuple(wavelength_range)
        self.distance_range = tuple(distance_range)

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "attractor": self.attractor,
            "tpmstype": self.tpmstype,
            "wavelength_range": list(self.wavelength_range),
            "distance_range": list(self.distance_range),
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(
            data["attractor"],
            data["tpmstype"],
            tuple(data["wavelength_range"]),
            tuple(data["distance_range"]),
        )

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def tpmstype(self):
        return self._tpmstype

    @tpmstype.setter
    def tpmstype(self, tpmstype):
        self._tpmstype = resolve_tpmstype(tpmstype)

    @property
    def typename(self):
        return TPMSTYPES[self.tpmstype]

    def __repr__(self):
        return "TPMSAttractor({0!r},{1},{2},{3})".format(
            self.attractor, self.tpmstype, self.wavelength_range, self.distance_range
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def _factor(self, d, np):
        """Remap an attractor distance to a wavelength/pi factor."""
        d0, d1 = self.distance_range
        w0, w1 = self.wavelength_range
        t = np.clip((d - d0) / (d1 - d0), 0.0, 1.0)
        return (w0 + t * (w1 - w0)) / pi

    def get_distance(self, point):
        import numpy as np

        x, y, z = point
        f = self._factor(self.attractor.get_distance(point), np)
        return float(tpms_field(self.tpmstype, x / f, y / f, z / f))

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        f = self._factor(self.attractor.get_distance_numpy(x, y, z), np)
        return tpms_field(self.tpmstype, x / f, y / f, z / f)
