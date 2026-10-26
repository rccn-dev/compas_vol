"""Pytest configuration shipped with the package.

Running the suite with ``--doctest-modules --pyargs compas_vol`` imports every
module. A few of them sit behind optional extras -- the viewer scene object
subclasses a ``compas_viewer`` class, and the iso-surfacing doctests need
``scikit-image``. Skip those when the corresponding extra is absent, so the
doctests still run on a core-only install.

This lives inside the package rather than at the repository root because
``--pyargs`` collects from the install location, and pytest only consults
conftest files along the collected path.
"""

import importlib.util

import pytest


def _available(name):
    return importlib.util.find_spec(name) is not None


#: Modules that cannot be imported, or whose doctests cannot run, without the
#: named optional dependency. Keyed by ``(parent directory, file name)``.
OPTIONAL_MODULES = {
    ("scene", "volobject.py"): "compas_viewer",
    ("meshing", "marching.py"): "skimage",
    ("meshing", "stl.py"): "skimage",
    ("processes", "field.py"): "skfmm",
    ("processes", "evolve.py"): "skfmm",
    ("processes", "generators.py"): "skfmm",
    ("processes", "growth.py"): "skfmm",
    ("processes", "morphology.py"): "skfmm",
    ("fabrication", "repair.py"): "skfmm",
    ("processes", "weathering.py"): "skfmm",
}


#: Single doctests that need an extra, in modules that otherwise do not. Keyed
#: by the doctest's name, as pytest reports it.
OPTIONAL_DOCTESTS = {
    "compas_vol.nodes.abrasion": "skfmm",
    "compas_vol.nodes.strata": "skfmm",
    "compas_vol.nodes.spinodal": "skfmm",
}


def pytest_ignore_collect(collection_path, config):
    requirement = OPTIONAL_MODULES.get((collection_path.parent.name, collection_path.name))
    if requirement and not _available(requirement):
        return True
    return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        requirement = OPTIONAL_DOCTESTS.get(item.name)
        if requirement and not _available(requirement):
            item.add_marker(pytest.mark.skip(reason="needs {}".format(requirement)))
