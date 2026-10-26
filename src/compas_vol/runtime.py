"""
********************************************************************************
compas_vol.runtime
********************************************************************************

.. currentmodule:: compas_vol.runtime

Where the package is running, and what it can do there.

compas_vol is meant to run unchanged in three places:

``headless``
    A plain Python process: scripts, tests, CI, a render farm. Results leave as
    STL or as COMPAS JSON.
``viewer``
    The same process with :mod:`compas_viewer` available, so objects can be
    added to a scene (see :mod:`compas_vol.scene`).
``rhino``
    Inside Rhino 8 / Grasshopper, whose embedded CPython 3.9 imports this
    package directly. Results leave as Rhino meshes.

The core package imports only ``compas`` and ``numpy``; everything heavier is
imported at the point of use. That keeps the Rhino and headless paths light,
but it also means a missing dependency surfaces deep inside a call, as
``No module named 'skimage'``, which does not tell a designer what to install.
:func:`require` is the single place that turns those into an instruction.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    context
    capabilities
    require
    report

"""

import importlib
import sys

__all__ = ["context", "capabilities", "require", "report"]


#: For each optional module: the extra that provides it, and what it is for.
#: Keeping this in one table is what makes the failure message consistent
#: wherever the import happens. An extra of ``None`` means the module cannot
#: be installed with pip at all -- it is supplied by the host application.
_PROVIDERS = {
    # compas depends on scipy, so in practice this is always present and the
    # meshing extra only adds scikit-image. It stays in the table so that a
    # broken environment still gets a message that names a version to install.
    "scipy": ("meshing", "grid filtering, labelling and interpolation"),
    "skimage": ("meshing", "marching-cubes iso-surfacing"),
    "skfmm": ("processes", "redistancing, which every process step depends on"),
    "compas_viewer": ("viewer", "the standalone OpenGL viewer"),
    "matplotlib": ("examples", "the field slice inspector used by the examples"),
    "Rhino": (None, "Rhino geometry; it exists only inside Rhino or Grasshopper"),
}

#: Filled by :func:`_detect_rhino` on first use. ``None`` means "not asked yet".
_RHINO = None


def _detect_rhino():
    """Return True if this interpreter is Rhino's.

    Rhino 8 embeds CPython 3.9 and injects its own ``Rhino`` module, which
    exists nowhere else. Checking :data:`sys.modules` first means the common
    case -- a normal Python process -- never pays for a failed import.
    """
    global _RHINO
    if _RHINO is None:
        if "Rhino" in sys.modules or "rhinoscriptsyntax" in sys.modules:
            _RHINO = True
        else:
            try:
                importlib.import_module("Rhino")
            except ImportError:
                _RHINO = False
            else:
                _RHINO = True
    return _RHINO


def _available(name):
    """Return True if module `name` can be imported, without keeping it loaded twice."""
    if name in sys.modules:
        return True
    try:
        importlib.import_module(name)
    except ImportError:
        return False
    return True


def context():
    """Name the context this process is running in.

    Returns
    -------
    str
        ``"rhino"``, ``"viewer"`` or ``"headless"``.

    Notes
    -----
    ``"rhino"`` wins over ``"viewer"``: inside Rhino the host application owns
    the display, so :mod:`compas_viewer` is not the way to show anything even
    if it happens to be importable.

    Examples
    --------
    >>> context() in {"rhino", "viewer", "headless"}
    True

    """
    if _detect_rhino():
        return "rhino"
    if _available("compas_viewer"):
        return "viewer"
    return "headless"


def capabilities():
    """Report which optional dependencies are importable here.

    Returns
    -------
    dict
        Module name mapped to ``True`` or ``False``, in the order of
        :data:`_PROVIDERS`.

    Examples
    --------
    >>> caps = capabilities()
    >>> sorted(caps) == sorted(["Rhino", "compas_viewer", "matplotlib", "scipy", "skfmm", "skimage"])
    True
    >>> all(isinstance(v, bool) for v in caps.values())
    True

    """
    return dict((name, _available(name)) for name in _PROVIDERS)


def require(name):
    """Import an optional module, or explain how to install it.

    Parameters
    ----------
    name : str
        A module path, e.g. ``"scipy.ndimage"``. The first component decides
        which extra is named in the error.

    Returns
    -------
    module

    Raises
    ------
    ImportError
        If the module is not installed. The message names the extra to install
        and what it is needed for.

    Examples
    --------
    >>> require("json").__name__
    'json'
    >>> require("skimage.measure")                       # doctest: +SKIP
    <module 'skimage.measure' ...>

    """
    try:
        return importlib.import_module(name)
    except ImportError as error:
        root = name.split(".")[0]
        if root not in _PROVIDERS:
            raise
        extra, purpose = _PROVIDERS[root]
        if extra is None:
            raise ImportError("{} needs {}, which provides {}.".format(name, root, purpose)) from error
        raise ImportError(
            "{} needs {}, which compas_vol keeps optional: install it with "
            'pip install "compas-vol[{}]". It provides {}.'.format(name, root, extra, purpose)
        ) from error


def report():
    """Describe the context and its capabilities, for a human.

    Returns
    -------
    str
        One line per fact, ready to print or to drive a Grasshopper panel.

    Examples
    --------
    >>> print(report())                                  # doctest: +ELLIPSIS
    compas_vol ... on Python ...
    context      : ...

    """
    from compas_vol import __version__

    lines = [
        "compas_vol {} on Python {}.{}.{}".format(__version__, *sys.version_info[:3]),
        "context      : {}".format(context()),
    ]
    for name, present in capabilities().items():
        extra, purpose = _PROVIDERS[name]
        mark = "yes" if present else "no "
        lines.append("{:<13}: {}  [{}] {}".format(name, mark, extra or "host", purpose))
    return "\n".join(lines)
