********************************************************************************
Porting from COMPAS 1
********************************************************************************

How this fork differs from
`dbt-ethz/compas_vol <https://github.com/dbt-ethz/compas_vol>`_: changes forced
by COMPAS 2, defects fixed, and stubs filled in. Use it to migrate scripts.

API changes forced by COMPAS 2
==============================

Old spellings are kept as aliases where that is unambiguous.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - COMPAS 1
     - Here
   * - ``compas.PRECISION``
     - ``compas.tolerance.TOL`` (via ``compas_vol.base.format_number``)
   * - ``Box(frame, x, y, z)``
     - ``Box(x, y, z, frame=frame)``
   * - ``Sphere(point, r)``
     - ``Sphere(r, point=point)``
   * - ``Cylinder(circle, h)``
     - ``Cylinder(r, h, frame=frame)``
   * - ``Cone(circle, h)``
     - ``Cone(r, h, frame=frame)``
   * - ``Torus(plane, ra, rp)``
     - ``Torus(ra, rp, frame=frame)``
   * - ``Sphere.center``
     - ``Sphere.base`` (``VolSphere.center`` still works)
   * - ``Cone.plane``
     - removed upstream; ``Cone.frame`` is used instead
   * - ``.to_data()`` / ``.from_data()``
     - ``__data__`` / ``__from_data__``, i.e. ``json_dumps`` / ``json_loads``
   * - ``marching_cubes_lewiner``
     - ``skimage.measure.marching_cubes``
   * - ``scipy.ndimage.filters``
     - ``scipy.ndimage``
   * - ``compas.utilities.remap_values``
     - ``compas.itertools.remap_values``
   * - ``PlatonicSolid(r, type=...)``
     - ``PlatonicSolid(r, solid_type=...)`` (no builtin shadowing)

Transformations
---------------

``np.array([x, y, z, 1], dtype=object)`` is replaced throughout by
:func:`compas_vol.base.transform_numpy`. The object-dtype version was slow, and
the variants without ``dtype=object`` (``VolEllipsoid``, ``VolTorus``,
``Twist``) raise on NumPy 2.

Serialization
-------------

The ``eval(repr(obj))`` transport is gone;
:func:`compas_vol.utilities.dumps_tree` and
:func:`compas_vol.utilities.loads_tree` use COMPAS JSON.

Visualization
-------------

``ipyvolume`` and ``meshplot`` no longer work on current Python. Drawing is
scene-object registration (:mod:`compas_vol.scene`), the COMPAS 2 pattern.

Correctness fixes
=================

Broken in the original regardless of COMPAS version; each has a regression
test in ``tests/test_regressions.py``.

Query points were mutated in place
    Every object working in a local frame called ``point.transform(...)`` on the
    caller's own :class:`compas.geometry.Point`, so calling ``get_distance(p)``
    twice with the same point gave two different answers.

``Sine`` could not be constructed
    ``self.f = f`` with no ``f`` in scope — a ``NameError`` on every
    instantiation.

``Division.__repr__`` and ``Multiplication.__repr__``
    Both referenced a ``self.objs`` attribute that neither class defined.

``Blend`` returned ``None``
    For any ramp type other than 0 or 1, the method fell off the end.

``TPMSPolar``
    Called ``math.arctan2``, which does not exist. Its ``wavelength`` property
    read an unassigned attribute, and its wavelength argument was never applied.

``Voronoi`` was not a Voronoi field
    It mixed in the squared distance from the *world origin* to the nearest
    seed — a term independent of the query point. It also imported from
    ``numpy.core``, removed in NumPy 2, so the module failed to import at all.

``Twist`` ignored its ``angle``
    The single-point path rotated by ``distance / 10``; the vectorized path
    applied one fixed 10-radian rotation to every point.

``SmoothUnionList.get_distance_numpy`` returned a transposed grid
    It transposed the stack and then reduced the wrong axis.

``Gradient.get_gradient_numpy``
    Normalized over a reduced axis without re-inserting it, so it broadcast
    wrongly.

``Octree`` was entirely non-functional
    It never stored the object to sample, called ``get_distance`` with three
    loose coordinates, and read a ``node.pos`` attribute that ``OctNode`` never
    defined.

The dodecahedron disagreed with itself
    The vectorized branch used ``(1 + sqrt(5)/2)`` where the scalar branch used
    ``(1 + sqrt(5))/2``.

``Heart.get_distance`` ignored its frame
    While ``get_distance_numpy`` honoured it.

Meshes came out translated
    Marching cubes returns grid-relative coordinates, and the old helpers never
    added the grid origin back.

``get_iso_mesh`` / ``get_iso_vfs`` only ever worked for boxes
    Both hard-coded a ``VolBox`` reconstruction regardless of what they were
    passed.

A missing comma in ``__all__``
    ``__all__`` in ``combinations`` silently concatenated ``'SmoothUnionList'``
    and ``'SmoothIntersection'`` into a single name.

Stubs filled in
===============

:class:`~compas_vol.primitives.GDF` and :class:`~compas_vol.analysis.Curvature`
    Raised ``NotImplementedError`` or were empty stubs. Both are implemented.

:class:`~compas_vol.microstructures.TPMSAttractor`
    Was a partial copy of :class:`~compas_vol.microstructures.TPMS` with its
    attractor logic left commented out as Rhino-specific code. It now grades
    wavelength by distance to any volumetric object.
