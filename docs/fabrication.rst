********************************************************************************
Fabrication
********************************************************************************

:mod:`compas_vol.fabrication` checks a sampled model the way a slicer would,
and reports numbers:

.. code-block:: python

    from compas_vol.fabrication import inspect

    report = inspect(field, angle=45, min_wall=1.6)
    print(report)

.. code-block:: none

    size           : 100.4 x 100.3 x 100.1 mm, 269 cm3
    pieces         : 1
    sealed cavities: 1  (0.3 cm3 trapped)
    overhang       : 15% of the surface past 45 degrees
    mid-air starts : 0 regions, 0.0 cm2
    wall thickness : 3.2 mm typical, 2.1 mm thinnest, 0.0% under 1.6 mm
    verdict        : 1 problem(s)
      - 1 sealed cavities holding 0.3 cm3

The model's lowest layer is the build plate; the face resting on it is not an overhang. Wall thickness is read from the
field, which is sub-voxel; a distance transform of the voxels would add about a
voxel to every thin wall. Overhang and mid-air checks assume printing upwards
in Z.

Each finding has a repair, which reports what it changed:

.. list-table::
   :widths: 35 65

   * - :func:`~compas_vol.fabrication.keep_largest`
     - drop pieces that came apart; returns the share removed
   * - :func:`~compas_vol.fabrication.drain_voids`
     - vent sealed cavities
   * - :func:`~compas_vol.fabrication.make_self_supporting`
     - add material under overhangs
   * - :func:`~compas_vol.processes.opened`
     - remove everything thinner than the process can hold

The repairs redistance, so they need the ``processes`` extra.
:func:`compas_vol.meshing.is_watertight` checks the final mesh as an STL reader
would.
