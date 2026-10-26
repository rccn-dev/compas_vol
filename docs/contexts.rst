********************************************************************************
Contexts
********************************************************************************

The same code runs in three places:

**headless**
    A plain Python process: long runs, and results written as STL or JSON.

**with compas_viewer**
    The same process with a viewer attached.

**in Grasshopper**
    Rhino 8 embeds CPython 3.9, so the package imports there directly. See
    :doc:`grasshopper`.

Three rules keep it that way. The core imports only ``compas`` and ``numpy``;
everything heavier is imported where it is used. The floor is Python 3.9, and
CI runs the suite on 3.9 and 3.13. Nothing in the package draws: the viewer is
a COMPAS plugin, and Grasshopper converts geometry in its components.

Which context am I in?
======================

.. code-block:: python

    >>> from compas_vol.runtime import context, report
    >>> context()                                   # doctest: +SKIP
    'headless'
    >>> print(report())                             # doctest: +SKIP
    compas_vol 0.2.0 on Python 3.9.10
    context      : rhino
    scipy        : yes  [meshing] grid filtering, labelling and interpolation
    skimage      : yes  [meshing] marching-cubes iso-surfacing
    skfmm        : no   [processes] redistancing, which every process step depends on
    ...

A missing optional dependency raises an :class:`ImportError` naming the extra
to install::

    ImportError: skimage.measure needs skimage, which compas_vol keeps
    optional: install it with pip install "compas-vol[meshing]". It provides
    marching-cubes iso-surfacing.

``scripts/check_headless.py`` checks both in CI, against an install with only
compas and numpy.

Headless
========

.. code-block:: python

    from compas.geometry import Sphere
    from compas_vol.meshing import export_stl
    from compas_vol.primitives import VolSphere

    export_stl(VolSphere(Sphere(50.0)), "ball.stl", bounds=60.0, resolution=400)

:func:`~compas_vol.meshing.export_stl` writes arrays straight to the file,
about 45x faster than building a COMPAS mesh and calling ``to_stl``.

With compas_viewer
==================

.. code-block:: python

    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(VolSphere(Sphere(50.0)), bounds=60.0, resolution=128)
    viewer.scene.add(some_box, show_faces=False)    # alongside any COMPAS object
    viewer.show()

Volumetric objects are registered scene objects (:mod:`compas_vol.scene`), so
``scene.add`` takes them like any COMPAS geometry. Sampling parameters ride on
the call, as ``u``/``v`` do for a sphere. ``bounds`` has no default: a field
has no extent of its own. Only the viewer context is implemented; Rhino and
Blender scene objects would go in the same subpackage.
