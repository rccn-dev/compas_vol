********************************************************************************
Examples
********************************************************************************

All examples live in the ``examples/`` directory of the repository and are
runnable as-is::

    $ uv sync --extra examples

Single operations
=================

``examples/*.py`` are short ports of the original scripts, one idea each —
extrusion, the four booleans, smooth booleans, morph, lattice, TPMS, Voronoi,
gradient and octree::

    $ uv run --extra all python examples/example_tpms.py

Modelling studies
=================

``examples/vol_mesh_examples/`` holds fuller studies. Each opens the viewer with
the meshed result; closing it opens an interactive slice through the signed
distance field, where a slider moves the cutting plane — blue is inside, red is
outside, and the black contour is the surface that gets meshed::

    $ uv run python examples/vol_mesh_examples/8_morphing_microstructure.py

.. list-table::
   :header-rows: 1
   :widths: 32 48 20

   * - Script
     - What it shows
     - Theme
   * - ``template.py``
     - the full pipeline written out step by step, no helpers
     - reference
   * - ``1_extrusion.py``
     - a star polygon extruded along a tilted frame
     - primitives
   * - ``2_intersection.py``
     - sphere ∩ filleted box
     - CSG
   * - ``3_union.py``
     - sphere ∪ box, with the hard seam a union leaves
     - CSG
   * - ``4_smooth_union.py``
     - the same pair blended
     - CSG
   * - ``5_lattice.py``
     - a periodic strut lattice trimmed to a cube
     - microstructure
   * - ``6_tpms.py``
     - a TPMS shell with thickness graded by a plane
     - microstructure
   * - ``7_graded_tpms.py``
     - **cell size** driven by distance to an attractor
     - graded
   * - ``8_morphing_microstructure.py``
     - **cell type** morphing gyroid → Schwartz-P across the part
     - graded
   * - ``9_twisted_lattice.py``
     - a lattice sheared into a helix by warping the domain
     - non-linear
   * - ``10_graded_shell.py``
     - wall density graded radially, ~25% at the core to ~12% at the rim
     - graded
   * - ``11_graded_voronoi.py``
     - aperiodic cells with a seed-density gradient
     - stochastic
   * - ``12_field_math.py``
     - arithmetic on fields, producing surfaces CSG cannot
     - non-linear

The first six are ordinary constructive modelling. The last six are the ones
worth reading if you already know CSG: none of them is a boolean of two finished
shapes, and each varies a property continuously through space rather than tiling
one unit cell.
