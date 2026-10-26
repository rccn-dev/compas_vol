********************************************************************************
Introduction
********************************************************************************

A volumetric object is a function

.. math::

    f : \mathbb{R}^3 \rightarrow \mathbb{R}

returning the **signed distance** to its surface: negative inside, zero on the
surface, positive outside. The surface is computed only when something has to
be drawn or made.

Why signed distance functions
=============================

Operations on the object are operations on the function:

* **Booleans** are ``min`` and ``max``. They cannot fail on degenerate input
  or leave slivers.
* **Fillets and blends** use a smooth minimum, with a chosen radius.
* **Offsets and shells** are arithmetic on the distance.
* **Lattices and TPMS** are periodic functions, evaluated only where needed.
* **Grading** is a parameter that varies through space: wall thickness, cell
  size, even cell type.

The cost is meshing: a field is sampled on a grid and polygonised, which
scales with the cube of the resolution. Modelling is exact; only the final
surface is approximate.

How the package is organised
============================

Every object subclasses :class:`compas_vol.base.VolObject` and has two methods,
tested to agree for every class:

``get_distance(point)``
    The distance at one point.

``get_distance_numpy(x, y, z)``
    The distance over a grid of ``np.ogrid`` arrays. Meshing and viewing use
    this one.

.. list-table::
   :widths: 30 70

   * - :mod:`compas_vol.primitives`
     - boxes, spheres, cylinders, extrusions, platonic solids, sampled grids
   * - :mod:`compas_vol.combinations`
     - booleans, smooth booleans, morphs, field arithmetic
   * - :mod:`compas_vol.modifications`
     - shells, offsets, twists, remaps, blur
   * - :mod:`compas_vol.microstructures`
     - lattices, TPMS, Voronoi
   * - :mod:`compas_vol.analysis`
     - gradient and curvature
   * - :mod:`compas_vol.meshing`
     - sampling, iso-surfacing, STL export, octree
   * - :mod:`compas_vol.processes`
     - erosion, growth, phase separation: see :doc:`processes`
   * - :mod:`compas_vol.fabrication`
     - printability checks and repairs: see :doc:`fabrication`
   * - :mod:`compas_vol.assembly`
     - cutting a model into pieces: see :doc:`assembly`
   * - :mod:`compas_vol.nodes`, :mod:`compas_vol.ghpython`
     - the Grasshopper components: see :doc:`grasshopper`
   * - :mod:`compas_vol.scene`, :mod:`compas_vol.runtime`
     - viewer integration and context checks: see :doc:`contexts`
