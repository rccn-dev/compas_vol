********************************************************************************
Installation
********************************************************************************

.. highlight:: bash

Requirements
============

* Python 3.13 or newer
* COMPAS 2.15 or newer
* NumPy 2.0 or newer

The COMPAS 1 releases of this package will not work here, and this release will
not work on COMPAS 1. See :doc:`../porting`.

From the repository
===================

This fork is not on PyPI. Install it from GitHub::

    $ pip install git+https://github.com/rccn-dev/compas_vol

Or, for a checkout you intend to work on, using `uv <https://docs.astral.sh/uv/>`_::

    $ git clone https://github.com/rccn-dev/compas_vol
    $ cd compas_vol
    $ uv sync

Optional extras
===============

The core install depends only on ``compas`` and ``numpy``. Everything heavier is
optional:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Extra
     - Adds
     - Needed for
   * - ``meshing``
     - scikit-image, scipy
     - Iso-surfacing (:mod:`compas_vol.meshing`) and :class:`~compas_vol.modifications.Blur`
   * - ``viewer``
     - compas_viewer
     - The standalone OpenGL viewer
   * - ``examples``
     - the above, plus matplotlib
     - Everything in ``examples/``, including the field slice inspector
   * - ``all``
     - all of the above
     -

::

    $ uv sync --extra meshing
    $ uv sync --extra viewer
    $ uv sync --extra all

The ``viewer`` extra pulls in PySide6, which is a large download. It is kept
optional so that using the package as a modelling library — or on a headless
machine — does not require it.

With pip, the same extras are available::

    $ pip install "compas_vol[all] @ git+https://github.com/rccn-dev/compas_vol"

Verifying the installation
==========================

::

    $ uv run --extra meshing python -m pytest

The test suite parametrizes every volumetric class over a shared set of checks,
so a clean run is a reasonable statement that the install is sound.
