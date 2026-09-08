from math import pi

from compas_vol.base import VolObject
from compas_vol.base import format_number

TPMSTYPES = ["Gyroid", "SchwartzP", "Diamond", "Neovius", "Lidinoid", "FischerKoch"]
_TPMSTYPES_LOWER = [s.lower() for s in TPMSTYPES]


def resolve_tpmstype(tpmstype):
    """Normalise a TPMS type given as a name or an index to an index."""
    if isinstance(tpmstype, str):
        try:
            return _TPMSTYPES_LOWER.index(tpmstype.lower())
        except ValueError:
            return 0
    return max(0, min(int(tpmstype), len(TPMSTYPES) - 1))


def tpms_field(tpmstype, px, py, pz):
    """Evaluate a TPMS implicit function at the given (already scaled) coordinates.

    Uses NumPy ufuncs throughout, which operate on plain floats as well as on
    arrays. Sharing one implementation between the single-point and vectorized
    paths is what keeps them from drifting apart -- in COMPAS 1 they were
    written out twice, and :class:`TPMSPolar` called ``math.arctan2``, a
    function that does not exist.
    """
    import numpy as np

    if tpmstype == 0:  # Gyroid
        return np.sin(px) * np.cos(py) + np.sin(py) * np.cos(pz) + np.sin(pz) * np.cos(px)
    if tpmstype == 1:  # SchwartzP
        return np.cos(px) + np.cos(py) + np.cos(pz)
    if tpmstype == 2:  # Diamond
        return (
            np.sin(px) * np.sin(py) * np.sin(pz)
            + np.sin(px) * np.cos(py) * np.cos(pz)
            + np.cos(px) * np.sin(py) * np.cos(pz)
            + np.cos(px) * np.cos(py) * np.sin(pz)
        )
    if tpmstype == 3:  # Neovius
        return (
            3 * np.cos(px) + np.cos(py) + np.cos(pz) + 4 * np.cos(px) * np.cos(py) * np.cos(pz)
        )
    if tpmstype == 4:  # Lidinoid
        return (
            0.5
            * (
                np.sin(2 * px) * np.cos(py) * np.sin(pz)
                + np.sin(2 * py) * np.cos(py) * np.sin(px)
                + np.sin(2 * pz) * np.cos(px) * np.sin(pz)
            )
            - 0.5
            * (
                np.cos(2 * px) * np.cos(2 * py)
                + np.cos(2 * py) * np.cos(2 * pz)
                + np.cos(2 * pz) * np.cos(2 * px)
            )
            + 0.15
        )
    if tpmstype == 5:  # FischerKoch
        return (
            np.cos(2 * px) * np.sin(py) * np.cos(pz)
            + np.cos(2 * py) * np.sin(pz) * np.cos(px)
            + np.cos(2 * pz) * np.sin(px) * np.cos(py)
        )
    raise ValueError("Unknown TPMS type: {!r}".format(tpmstype))


class TPMS(VolObject):
    """A triply periodic minimal surface, defined by a type and a wavelength.

    The field is a trigonometric approximation of the surface, not a metric
    distance field.

    Parameters
    ----------
    tpmstype : int | str
        The surface type, as an index into :data:`TPMSTYPES` or as a name.
        One of Gyroid, SchwartzP, Diamond, Neovius, Lidinoid, FischerKoch.
    wavelength : float
        The wavelength of the trigonometric function.

    Examples
    --------
    >>> from compas_vol.microstructures import TPMS
    >>> a = TPMS(tpmstype='Gyroid', wavelength=5.0)
    >>> a.tpmstype
    0
    >>> round(a.get_distance([0, 0, 0]), 6)
    0.0
    """

    def __init__(self, tpmstype=0, wavelength=1.0, name=None):
        super().__init__(name=name)
        self._tpmstype = None
        self._wavelength = None
        self.tpmstype = tpmstype
        self.wavelength = wavelength

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"tpmstype": self.tpmstype, "wavelength": self.wavelength}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["tpmstype"], data["wavelength"])

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
        """float: The wavelength of the TPMS."""
        return self._wavelength

    @wavelength.setter
    def wavelength(self, wavelength):
        self._wavelength = float(wavelength)
        self._factor = self._wavelength / pi

    def __repr__(self):
        return "TPMS({0},{1})".format(self.tpmstype, format_number(self.wavelength))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        x, y, z = point
        f = self._factor
        return float(tpms_field(self.tpmstype, x / f, y / f, z / f))

    def get_distance_numpy(self, x, y, z):
        f = self._factor
        return tpms_field(self.tpmstype, x / f, y / f, z / f)
