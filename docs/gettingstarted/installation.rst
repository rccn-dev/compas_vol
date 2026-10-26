********************************************************************************
Installation
********************************************************************************

.. highlight:: bash

Requires Python 3.9 or newer (Rhino 8 embeds 3.9), COMPAS 2.15 or newer and
NumPy 2. It does not work with COMPAS 1; see :doc:`../porting`.

The fork is not on PyPI. Install it from GitHub::

    $ pip install git+https://github.com/rccn-dev/compas_vol

or, to work on it, with `uv <https://docs.astral.sh/uv/>`_::

    $ git clone https://github.com/rccn-dev/compas_vol
    $ cd compas_vol
    $ uv sync

Extras
======

The core depends only on ``compas`` and ``numpy``.

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Extra
     - Adds
     - For
   * - ``meshing``
     - scikit-image, scipy
     - :mod:`compas_vol.meshing`, :class:`~compas_vol.modifications.Blur`
   * - ``processes``
     - scikit-fmm
     - :mod:`compas_vol.processes`, the repairs in :mod:`compas_vol.fabrication`
   * - ``viewer``
     - compas_viewer (and PySide6, a large download)
     - the standalone viewer
   * - ``examples``
     - all of the above, plus matplotlib
     - ``examples/``
   * - ``all``
     - everything
     -

::

    $ uv sync --extra meshing
    $ pip install "compas_vol[all] @ git+https://github.com/rccn-dev/compas_vol"

Check the install with ``uv run --extra meshing python -m pytest``.
