from math import pi

from compas_vol.base import VolObject
from compas_vol.base import format_number

from .tpms import TPMSTYPES
from .tpms import resolve_tpmstype
from .tpms import tpms_field


class TPMSPolar(VolObject):
    """A triply periodic minimal surface evaluated in cylindrical coordinates.

    The cartesian ``(x, y)`` plane is replaced by ``(radius, angle)``, so the
    cells wrap around the Z axis instead of tiling a square grid.

    The COMPAS 1 version was unusable: it called ``math.arctan2`` (a NumPy
    name), its ``wavelength`` property read an attribute that was never
    assigned, and the ``waveLength`` constructor argument was never applied to
    the coordinates at all.

    Parameters
    ----------
    tpmstype : int | str
        The surface type, as an index into :data:`compas_vol.microstructures.TPMSTYPES`
        or as a name.
    wavelength : float
        The wavelength along the radial and Z directions.
    thickness : float
        The thickness of the surface.
    polar : float
        The number of angular repetitions around the Z axis.

    Examples
    --------
    >>> from compas_vol.microstructures import TPMSPolar
    >>> t = TPMSPolar('Gyroid', 5.0, 0.1, 6)
    >>> isinstance(t.get_distance([3, 4, 0]), float)
    True
    """

    def __init__(self, tpmstype=0, wavelength=1.0, thickness=0.1, polar=6.0, name=None):
        super().__init__(name=name)
        self._tpmstype = None
        self._wavelength = None
        self.tpmstype = tpmstype
        self.wavelength = wavelength
        self.thickness = thickness
        self.polar = polar

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "tpmstype": self.tpmstype,
            "wavelength": self.wavelength,
            "thickness": self.thickness,
            "polar": self.polar,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["tpmstype"], data["wavelength"], data["thickness"], data["polar"])

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

    @property
    def wavelength(self):
        return self._wavelength

    @wavelength.setter
    def wavelength(self, wavelength):
        self._wavelength = float(wavelength)
        self._factor = self._wavelength / pi

    def __repr__(self):
        return "TPMSPolar({0},{1},{2},{3})".format(
            self.tpmstype,
            format_number(self.wavelength),
            format_number(self.thickness),
            format_number(self.polar),
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def _polar_coords(self, x, y, z, np):
        f = self._factor
        px = np.sqrt(x**2 + y**2) / f
        py = np.arctan2(y, x) * self.polar
        pz = z / f
        return px, py, pz

    def get_distance(self, point):
        import numpy as np

        x, y, z = point
        px, py, pz = self._polar_coords(x, y, z, np)
        return float(tpms_field(self.tpmstype, px, py, pz)) - self.thickness / 2.0

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        # ogrid components must be broadcast before arctan2 sees them.
        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        bx, by, bz = (np.broadcast_to(c, shape) for c in (x, y, z))
        px, py, pz = self._polar_coords(bx, by, bz, np)
        return tpms_field(self.tpmstype, px, py, pz) - self.thickness / 2.0
