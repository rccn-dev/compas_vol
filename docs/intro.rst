********************************************************************************
Introduction
********************************************************************************

Volumetric modelling represents geometry as a *field* rather than as a
boundary. Instead of storing vertices, edges and faces, an object is a function

.. math::

    f : \mathbb{R}^3 \rightarrow \mathbb{R}

that returns, for any point in space, the **signed distance** to the surface of
the object: negative inside, zero on the surface, positive outside. The surface
itself is the zero level set of that function, and it is only ever computed when
something actually needs to be drawn or fabricated.

Why signed distance functions
=============================

Because the representation is a function, operations on it are function
composition, and they are exact, cheap and always well defined:

* **Booleans** are ``min`` and ``max``. A union never produces a self-
  intersection, a subtraction never leaves a sliver, and neither can fail on
  degenerate input — the failure modes of mesh and B-rep booleans simply do not
  exist here.
* **Fillets and blends** come free. Replacing ``min`` with a smooth minimum
  rounds the seam, with a radius you choose, at no modelling cost.
* **Offsets and shells** are arithmetic on the distance value itself.
* **Infinite and periodic structures** — lattices, triply periodic minimal
  surfaces — are just functions, so they cost nothing to define and are only
  ever evaluated inside the region you care about.
* **Graded structures** follow directly. Any parameter of the function may vary
  continuously through space, so wall thickness, cell size or even cell *type*
  can be driven by a field rather than tiled uniformly.

The last point is what makes the approach interesting for additive
manufacturing, where the fabrication process imposes no penalty for a part whose
internal structure varies everywhere.

The trade-off is that an implicit surface has to be sampled on a grid and
polygonized before it can be viewed or exported, and the cost of that scales
with the cube of the resolution. Modelling stays exact; only the final
extraction is approximate.

How this package is organized
=============================

Every object subclasses :class:`compas_vol.base.VolObject` and exposes the same
two methods:

``get_distance(point)``
    The signed distance at a single point, as a float.

``get_distance_numpy(x, y, z)``
    The signed distance over a whole grid at once, given ``np.ogrid`` arrays.

The two are tested to agree to machine precision for every class in the package.
The single-point form is for inspection and for embedding in other code; the
vectorized form is what meshing and viewing actually use, and it is several
orders of magnitude faster.

From there the package divides into:

:mod:`compas_vol.primitives`
    Base shapes — boxes, spheres, cylinders, tori, platonic solids, extrusions.

:mod:`compas_vol.combinations`
    Ways of putting two or more objects together — booleans, smooth booleans,
    morphs and field arithmetic.

:mod:`compas_vol.modifications`
    Operations on a single object — shells, twists, sine displacement, blur.

:mod:`compas_vol.microstructures`
    Periodic and stochastic infill — lattices, TPMS, Voronoi.

:mod:`compas_vol.analysis`
    Fields derived from a field — gradient and curvature.

:mod:`compas_vol.meshing`
    Sampling and iso-surfacing, plus an adaptive octree.

:mod:`compas_vol.scene`
    COMPAS 2 scene object registration, so volumetric objects can be added to a
    scene like any other COMPAS geometry.

Relation to the original
========================

The original ``compas_vol`` came out of research at Digital Building
Technologies, ETH Zurich, alongside the Grasshopper plugin *Axolotl*. It targets
COMPAS 1 and does not import against the current stack. This fork keeps the
architecture and the API shape, and updates the implementation. :doc:`porting`
lists every behavioural difference.
