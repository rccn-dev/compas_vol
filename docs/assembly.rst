********************************************************************************
Assembly
********************************************************************************

A field costs nothing to describe at any size, but sampling it does: a 6 m
canopy at 1 mm voxels is 216 billion samples. :mod:`compas_vol.assembly` cuts a
model into pieces that each fit a machine and fit in memory.

Cutting
=======

.. code-block:: python

    from compas_vol.assembly import Pins, segment

    assembly = segment(model, bounds, piece=400.0, clearance=0.4,
                       joint=Pins(diameter=8.0, depth=5.0, fit=0.15))

Each :class:`~compas_vol.assembly.Piece` is the model intersected with its box.
``clearance`` comes off every shared face; :class:`~compas_vol.assembly.Pins`
adds a pin and a socket across each, only where both sides have material.

``piece`` gives a grid. ``cells`` gives any non-overlapping boxes instead, so
cuts can follow the construction: beam faces, panel sizes. Faces two cells
share, including T-junctions, get the clearance and the joints.
:func:`~compas_vol.assembly.place_cuts` moves a cut, within a tolerance, to where
:func:`~compas_vol.assembly.section_cost` says it meets the most material.

A piece cut from a lattice is often several parts: struts held by material
outside the box come loose. :meth:`~compas_vol.assembly.Assembly.check` finds
them; :func:`~compas_vol.fabrication.keep_largest` drops them.

Building piece by piece
=======================

A process reads the surface around each point, so pieces processed separately
must still agree where they meet:

.. code-block:: python

    from compas_vol.assembly import Seams

    seams = Seams(assembly, step=2.0)
    for piece, finished, processed in assembly.build(weather, voxel=2.0, halo=16.0, seams=seams):
        ...                                    # one piece in memory at a time
    print(seams.summary())

* **Halo.** Each piece is processed over its box grown by ``halo``, so the
  process sees the neighbour's material at a cut, then cut back. Make the halo
  longer than any length the process measures with.
* **Lattice.** Pieces are sampled on a world lattice of spacing ``voxel``, so
  overlapping halos share their samples exactly.
* **Coherent noise.** Noise is a function of world coordinates, so every piece
  sees the same noise. A per-piece simulation such as
  :func:`~compas_vol.processes.spinodal` grows a different result in each box.

:class:`~compas_vol.assembly.Seams` compares neighbours on each shared face: the
gap between their surfaces, and the share of the face that one side calls solid
and the other void. :meth:`~compas_vol.assembly.Assembly.cost` quotes the whole
model against the largest piece at a given voxel and halo.

``examples/26_piece_by_piece.py`` is a small case.
`grid-roof <https://github.com/rccn-dev/grid-roof>`_ builds 53 pieces whose seams meet within about 2 mm at 40 mm voxels.
