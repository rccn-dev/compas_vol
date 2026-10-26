********************************************************************************
First Steps
********************************************************************************

Building a shape
================

Volumetric objects wrap COMPAS geometry and compose with each other. Nothing
is evaluated until it is asked for:

.. code-block:: python

    from compas.geometry import Box, Point, Sphere
    from compas_vol.primitives import VolBox, VolSphere
    from compas_vol.combinations import Subtraction

    shape = Subtraction(
        VolBox(Box(20, 15, 10), radius=2.5),
        VolSphere(Sphere(9, point=Point(5, 6, 0))),
    )

Evaluating the field
====================

.. code-block:: python

    import numpy as np

    shape.get_distance((0, 0, 0))                        # one point
    x, y, z = np.ogrid[-20:20:100j, -20:20:100j, -20:20:100j]
    field = shape.get_distance_numpy(x, y, z)            # a whole grid

Meshing and export
==================

.. code-block:: python

    from compas_vol.meshing import export_stl, generate_mesh, iso_surface, sample

    mesh = generate_mesh(shape, bounds=20.0, resolution=100)     # a COMPAS Mesh
    export_stl(shape, "part.stl", bounds=20.0, resolution=200)   # straight to a file

    values, origin, spacing = sample(shape, bounds=20.0, resolution=64)
    vertices, faces = iso_surface(values, origin, spacing)       # a grid you already have

``bounds`` is a :class:`compas.geometry.Box`, a scalar ``s`` for the cube
``[-s, s]``, ``(xmin, ymin, zmin, xmax, ymax, zmax)``, or three ``(min, max)``
pairs. Use :func:`~compas_vol.meshing.export_stl` for files: building a COMPAS
mesh of a few million triangles costs more than sampling and meshing together.

Viewing
=======

Volumetric objects are COMPAS scene objects:

.. code-block:: python

    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(shape, bounds=20.0, resolution=100, opacity=0.5)
    viewer.show()

``bounds`` is required, because a field has no extent of its own: a TPMS is
infinite, and an intersection cannot report one.

Saving
======

Every object is a :class:`compas.data.Data`, so a whole tree round-trips
through COMPAS JSON:

.. code-block:: python

    from compas.data import json_dumps, json_loads

    restored = json_loads(json_dumps(shape))

Next: :doc:`../examples`, or :doc:`../processes` for geometry made by
erosion and growth.
