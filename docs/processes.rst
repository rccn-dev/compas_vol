********************************************************************************
Processes
********************************************************************************

:mod:`compas_vol.processes` makes geometry by process: a rock is weathered, a
coral is grown. The designer sets the mechanism and its rates; the form is what
the mechanism leaves. Requires the ``processes`` extra (scikit-fmm).

.. code-block:: python

    from compas_vol.processes import Field, abrasion, pitting, strata

    field = Field.from_object(massing, bounds=58.0, resolution=160)
    field = strata(field, thickness=15.0, dip=(0.22, 0.08), depth=3.0)
    field = pitting(field, depth=6.0, length=6.0)
    rock = abrasion(field, depth=2.0).to_volume()       # a VolGrid, ready to model with

.. list-table::
   :widths: 20 80

   * - weathering
     - ``abrasion``, ``differential``, ``pitting``, ``strata``, ``runoff``, ``jointing``
   * - growth
     - ``fingering``, ``accretion``, ``branching``, ``diffusion_limited``
   * - generators
     - ``spinodal``, ``reaction_diffusion``, ``fbm`` noise
   * - clean-up
     - ``opened`` (remove thin features), ``closed`` (fill narrow gaps)

One operator
============

Every process moves the surface along its normal at a speed that varies across
it. On a signed distance field :math:`\phi`, negative inside:

.. math::

   \phi \leftarrow \phi + v \, |\nabla \phi|

the level-set equation of Osher and Sethian (1988). Positive :math:`v` erodes,
negative :math:`v` grows. :func:`~compas_vol.processes.evolve` serves both;
processes differ only in their speed terms, which compose::

    from compas_vol.processes.terms import Convexity, Uniform

    speed = Uniform(0.25) * (1.0 + 2.0 * Convexity(length=9.0))

*Rates* are millimetres per step; *signals* are dimensionless. A rate times
signals is a rate.

Invariants
==========

**Every result is a distance field.** A varying speed breaks
:math:`|\nabla \phi| = 1`, and a 2 mm shell is only 2 mm thick if the field
measures millimetres. Each step therefore ends in a sub-voxel redistance by
fast marching (Sethian, 1996).

**Every parameter is a length**, including the length curvature is measured
against. Measured against the voxel size, every curvature term vanishes and
every process returns a blob.

**The grid is the way out.** :meth:`~compas_vol.processes.Field.to_volume`
returns a :class:`~compas_vol.primitives.VolGrid`, which can be shelled, cut,
filled with a lattice and exported like any other object.

**Results are repeatable.** Noise is a function of world coordinates, so a
finer grid resolves the same noise. Every process takes a ``seed``, and every
result records its history:

.. code-block:: python

    >>> print(rock.provenance())
    sample(source='VolEllipsoid(...)', bounds=(-58.0, ...), resolution=(160, 160, 160))
    strata(thickness=15.0, dip=(0.22, 0.08), depth=3.0, ...)
    pitting(depth=6.0, steps=12, length=6.0, ...)
    abrasion(depth=2.0, steps=12, length=9.0, edge_bias=2.0)

Constraints
===========

Some material must survive any process: a beam, a deck, a bearing face.
:meth:`~compas_vol.processes.Field.constrain` states it once::

    field = field.constrain(keep=beams, within=envelope, margin=150.0)

``keep`` is solid that must remain; ``within`` is the envelope growth may not
leave; ``margin`` fades a process out as it nears either. The constraint is
applied at every redistance, so every process honours it without a parameter of
its own, and :meth:`~compas_vol.processes.Field.violation` measures the result.
Copies and crops keep it. ``examples/23_constraints.py`` shows a rib weathered
with and without one.

Approximations
==============

They model the shape a mechanism leaves:

* There is no mass conservation, sediment transport or time in seconds.
  ``steps`` is a count; depths are millimetres of retreat.
* Shelter is measured by blurring the solid; concavity stands in for moisture.
* :func:`~compas_vol.processes.runoff` reads the model as a height field and
  ignores undersides.
* :func:`~compas_vol.processes.spinodal` works on the voxel lattice; its
  feature size is converted from millimetres.

Accuracy and cost
=================

Depth error is first order in the voxel size. A nominal 2 mm erosion of a
sphere:

======== ========
voxel    error
======== ========
1.50 mm  +6.2%
1.00 mm  +3.1%
0.67 mm  +0.5%
======== ========

At 160\ :sup:`3`, a one-shot displacement such as
:func:`~compas_vol.processes.strata` takes seconds, an iterated weathering
15-45 s, a hundred growth steps a few minutes. Features under about two voxels
do not survive, so the process resolution sets the finest detail.

Unstable growth
===============

Growth that runs faster where the surface bulges amplifies every wavelength,
down to one voxel. :func:`~compas_vol.processes.fingering` controls it with
curvature measured against a real length and a smoothed speed, whose smoothing
length sets the fold width. When a speed exceeds half a voxel per step,
:func:`~compas_vol.processes.evolve` scales the whole field down. Clipping each
point would flatten the differences the instability depends on and turn folding
into uniform growth.

References
==========

* Osher, S., Sethian, J. A. "Fronts propagating with curvature-dependent
  speed." *Journal of Computational Physics* 79(1), 1988.
* Sethian, J. A. "A fast marching level set method for monotonically
  advancing fronts." *PNAS* 93(4), 1996.
* Cahn, J. W., Hilliard, J. E. "Free energy of a nonuniform system I."
  *Journal of Chemical Physics* 28(2), 1958.
* Mullins, W. W., Sekerka, R. F. "Stability of a planar interface during
  solidification of a dilute binary alloy." *Journal of Applied Physics*
  35(2), 1964.
* Gray, P., Scott, S. K. "Autocatalytic reactions in the isothermal,
  continuous stirred tank reactor." *Chemical Engineering Science* 38(1), 1983.
* Runions, A., Lane, B., Prusinkiewicz, P. "Modeling trees with a space
  colonization algorithm." *Eurographics Workshop on Natural Phenomena*, 2007.
