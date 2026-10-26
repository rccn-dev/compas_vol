********************************************************************************
Examples
********************************************************************************

The examples are in ``examples/``, one idea per script, in reading order. Each
opens the COMPAS viewer on its result, then a slice through the field::

    $ uv sync --extra examples
    $ uv run python examples/02_booleans.py


Modelling
=========

.. list-table::
   :widths: 34 66

   * - ``01_extrusion.py``
     - a polygon extruded along a tilted frame
   * - ``02_booleans.py``
     - union, intersection and difference, hard and smooth
   * - ``03_blending.py``
     - morph, blend and offset
   * - ``04_field_math.py``
     - arithmetic on fields
   * - ``05_twisted_lattice.py``
     - domain warping: a lattice twisted into a helix
   * - ``06_gradient.py``
     - the gradient of a field, as colour
   * - ``07_octree.py``
     - adaptive refinement around the surface


Microstructures
===============

.. list-table::
   :widths: 34 66

   * - ``08_lattice.py``
     - a strut lattice trimmed to a cube
   * - ``09_polar.py``
     - a lattice and a TPMS wrapped around an axis
   * - ``10_tpms.py``
     - a graded TPMS shell, with the low-level ``TPMS``, ``Shell``, ``Overlay``
   * - ``11_tpms_catalogue.py``
     - every TPMS type with ``TPMSSolid``, dimensioned in millimetres
   * - ``12_sheet_vs_network.py``
     - one surface, three solids, with volume fractions

Start TPMS design with ``11``.


Grading
=======

.. list-table::
   :widths: 34 66

   * - ``13_graded_tpms.py``
     - cell size driven by an attractor
   * - ``14_morphing_microstructure.py``
     - cell type morphing from gyroid to Schwarz P
   * - ``15_graded_shell.py``
     - wall density graded radially
   * - ``16_graded_voronoi.py``
     - an aperiodic Voronoi foam with graded cells
   * - ``17_attractor_graded_wall.py``
     - wall thickness in millimetres, driven through ``Remap``
   * - ``18_cell_size_grading.py``
     - warping versus blending to grade cell size
   * - ``19_porous_rock.py``
     - massing, skin, graded interior and niches in one field


Processes
=========

Need the ``processes`` extra; they take seconds to minutes.

.. list-table::
   :widths: 34 66

   * - ``20_weathered_rock.py``
     - strata, jointing, pitting and abrasion in sequence
   * - ``21_spinodal_foam.py``
     - a bicontinuous foam by phase separation
   * - ``22_coral_growth.py``
     - differential growth, folding and uniform
   * - ``23_constraints.py``
     - weathering that leaves a rib intact
   * - ``24_process_to_print.py``
     - a weathered mass, skinned, filled, exported


Assembly
========

.. list-table::
   :widths: 34 66

   * - ``25_pavilion_assembly.py``
     - a 6 m canopy cut into pinned pieces
   * - ``26_piece_by_piece.py``
     - a processed model built one piece at a time
