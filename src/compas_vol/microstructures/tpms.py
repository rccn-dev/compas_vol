from math import pi

from compas_vol.base import VolObject
from compas_vol.base import format_number

#: Names of the available TPMS types, indexed as in :attr:`TPMS.tpmstype`.
#: New types are only ever appended, so integer indices stay stable.
TPMSTYPES = ["Gyroid", "SchwarzP", "Diamond", "Neovius", "Lidinoid", "FischerKoch", "IWP"]
_TPMSTYPES_LOWER = [s.lower() for s in TPMSTYPES]

#: Alternative spellings accepted by :func:`resolve_tpmstype`. The surface is
#: named after Hermann Schwarz; this package spelled it "SchwartzP" until 0.2.0,
#: so that spelling keeps working. "SchwarzD" is the usual name for Diamond.
_TPMSTYPE_ALIASES = {
    "schwartzp": 1,
    "primitive": 1,
    "p": 1,
    "schwarzd": 2,
    "schwartzd": 2,
    "d": 2,
    "g": 0,
    "fischerkochs": 5,
    "i-wp": 6,
    "schoeniwp": 6,
}


def resolve_tpmstype(tpmstype):
    """Normalise a TPMS type given as a name or an index to an index.

    Raises
    ------
    ValueError
        If the name or index is not a known type. Up to 0.2.0 an unknown name
        silently fell back to the gyroid, so a typo such as ``"SchwarzP"``
        produced the wrong surface without any warning.
    """
    if isinstance(tpmstype, str):
        key = tpmstype.lower().replace(" ", "").replace("_", "")
        if key in _TPMSTYPES_LOWER:
            return _TPMSTYPES_LOWER.index(key)
        if key in _TPMSTYPE_ALIASES:
            return _TPMSTYPE_ALIASES[key]
        raise ValueError("Unknown TPMS type {!r}. Available: {}".format(tpmstype, ", ".join(TPMSTYPES)))
    index = int(tpmstype)
    if not 0 <= index < len(TPMSTYPES):
        raise ValueError("TPMS type index must be in [0, {}], got {}".format(len(TPMSTYPES) - 1, index))
    return index


def tpms_field(tpmstype, px, py, pz):
    """Evaluate a TPMS implicit function at the given (already scaled) coordinates.

    Uses NumPy ufuncs throughout, which operate on plain floats as well as on
    arrays. Sharing one implementation between the single-point and vectorized
    paths is what keeps them from drifting apart -- in COMPAS 1 they were
    written out twice, and :class:`TPMSPolar` called ``math.arctan2``, a
    function that does not exist.

    Every expression is the *nodal approximation* of its surface: the leading
    terms of a Fourier series with the right symmetry, whose zero set has the
    same topology as the true minimal surface but not exactly zero mean
    curvature. All have period ``2 pi`` along each axis.
    """
    import numpy as np

    if tpmstype == 0:  # Gyroid
        return np.sin(px) * np.cos(py) + np.sin(py) * np.cos(pz) + np.sin(pz) * np.cos(px)
    if tpmstype == 1:  # Schwarz P (primitive)
        return np.cos(px) + np.cos(py) + np.cos(pz)
    if tpmstype == 2:  # Schwarz D (diamond)
        return (
            np.sin(px) * np.sin(py) * np.sin(pz)
            + np.sin(px) * np.cos(py) * np.cos(pz)
            + np.cos(px) * np.sin(py) * np.cos(pz)
            + np.cos(px) * np.cos(py) * np.sin(pz)
        )
    if tpmstype == 3:  # Neovius
        # Upstream had 3 * cos(x) + cos(y) + cos(z), which is not symmetric in
        # x, y and z and so is not the Neovius surface.
        return 3 * (np.cos(px) + np.cos(py) + np.cos(pz)) + 4 * np.cos(px) * np.cos(py) * np.cos(pz)
    if tpmstype == 4:  # Lidinoid
        return (
            0.5
            * (
                # Upstream had typos in the second and third terms, breaking the
                # x -> y -> z cyclic symmetry the lidinoid has.
                np.sin(2 * px) * np.cos(py) * np.sin(pz)
                + np.sin(2 * py) * np.cos(pz) * np.sin(px)
                + np.sin(2 * pz) * np.cos(px) * np.sin(py)
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
    if tpmstype == 6:  # Schoen I-WP
        return 2 * (np.cos(px) * np.cos(py) + np.cos(py) * np.cos(pz) + np.cos(pz) * np.cos(px)) - (
            np.cos(2 * px) + np.cos(2 * py) + np.cos(2 * pz)
        )
    raise ValueError("Unknown TPMS type: {!r}".format(tpmstype))


class TPMS(VolObject):
    """A triply periodic minimal surface, defined by a type and a wavelength.

    The field is a trigonometric (nodal) approximation of the surface, not a
    metric distance field, and it describes a surface with no thickness. For a
    printable solid with a wall thickness in model units, and a period given
    as the actual unit cell size, use :class:`TPMSSolid` instead.

    Note that ``wavelength`` is *half* the unit cell size: the field has
    period ``2 * wavelength`` along each axis.

    Parameters
    ----------
    tpmstype : int | str
        The surface type, as an index into :data:`TPMSTYPES` or as a name.
        One of Gyroid, SchwarzP, Diamond, Neovius, Lidinoid, FischerKoch, IWP.
    wavelength : float
        Half the period of the field along each axis.

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
