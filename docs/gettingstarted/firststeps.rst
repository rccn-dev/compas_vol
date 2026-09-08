********************************************************************************
First Steps
********************************************************************************

Building a shape
================

Volumetric objects wrap COMPAS geometry and compose with each other:

.. code-block:: python

    from compas.geometry import Box, Point, Sphere
    from compas_vol.primitives import VolBox, VolSphere
    from compas_vol.combinations import Subtraction

    shape = Subtraction(
        VolBox(Box(20, 15, 10), radius=2.5),
        VolSphere(Sphere(9, point=Point(5, 6, 0))),
    )

Nothing has been evaluated yet. ``shape`` is a function; it describes the
geometry without sampling it.

Evaluating the field
====================

.. code-block:: python

    shape.get_distance((0, 0, 0))     # -> float, signed distance at one point

For anything more than a handful of points, use the vectorized form, which
evaluates a whole grid at once:

.. code-block:: python

    import numpy as np

    x, y, z = np.ogrid[-20:20:100j, -20:20:100j, -20:20:100j]
    field = shape.get_distance_numpy(x, y, z)

Meshing
=======

.. code-block:: python

    from compas_vol.meshing import generate_mesh

    mesh = generate_mesh(shape, bounds=20.0, resolution=100)   # -> compas Mesh

``bounds`` accepts a :class:`compas.geometry.Box`, a scalar ``s`` for the cube
``[-s, s]``, a 6-sequence ``(xmin, ymin, zmin, xmax, ymax, zmax)``, or three
``(min, max)`` pairs.

Viewing
=======

Volumetric objects are registered COMPAS 2 scene objects, so they go into a
scene next to any other geometry:

.. code-block:: python

    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(shape, bounds=20.0, resolution=100, opacity=0.5)
    viewer.show()

An implicit surface has to be sampled before it can be drawn, so the sampling
parameters ride along on the ``scene.add`` call, exactly as ``u`` and ``v`` do
for a :class:`compas.geometry.Sphere`.

Unlike ``u``/``v``, **there is no sensible default for** ``bounds``, and it is
required. A :class:`~compas_vol.microstructures.TPMS` or
:class:`~compas_vol.microstructures.Lattice` is infinite, and an
:class:`~compas_vol.combinations.Intersection` cannot report an extent, so the
caller has to say where to look. Omitting it raises with an explanatory message.

Serialization
=============

Every volumetric object is a :class:`compas.data.Data` subclass, so whole CSG
trees round-trip through COMPAS JSON, children included:

.. code-block:: python

    from compas.data import json_dumps, json_loads

    restored = json_loads(json_dumps(shape))

Where next
==========

* :doc:`../examples` — runnable scripts, from single operations to graded
  microstructures.
* :doc:`../api` — the full API reference.
