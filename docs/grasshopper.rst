********************************************************************************
Grasshopper
********************************************************************************

The components sit under a **COMPAS Vol** tab. Each is a thin wrapper of one
function in :mod:`compas_vol.nodes`, with the same inputs in the same order.

Installing
==========

Rhino 8 has its own Python 3.9, so a terminal install does not reach it: install the
package into Rhino's Python, then the components.

#. From a clone of this repository, install it into Rhino's Python:

   .. code-block:: bash

       # macOS
       ~/.rhinocode/py39-rh8/python3.9 -m pip install -e "./compas_vol[meshing,processes]"

   .. code-block:: powershell

       # Windows (PowerShell)
       & "$env:USERPROFILE\.rhinocode\py39-rh8\python.exe" -m pip install -e ".\compas_vol[meshing,processes]"

   scikit-fmm, which the processes need, compiles from source on macOS and needs the Xcode
   command line tools; Windows gets a wheel.

#. Download ``compas_vol-ghuser.zip`` from the
   `releases <https://github.com/rccn-dev/compas_vol/releases>`_ and unzip it into
   Grasshopper's User Object folder (*File › Special Folders › User Object Folder*).
#. Restart Rhino. **Volumetric Info** lists what is installed.

To work on compas_vol itself, ``scripts/ghuser dev`` builds the components and links them
into Grasshopper, importing the package from ``src/`` (see :doc:`development`).

Components
==========

==================== ================ ==========================================
Component            Tab              Does
==================== ================ ==========================================
Volumetric Sphere    Primitives       a sphere
Volumetric Box       Primitives       a box, with optional edge fillets
Volumetric Cylinder  Primitives       a cylinder
Volumetric TPMS      Microstructures  a gyroid and its relatives, thickened
Volumetric Boolean   Operations       union, intersection, difference, blended
Volumetric Shell     Operations       an even wall around a surface
Volumetric Mesh      Meshing          sample over a box into a Rhino mesh
Volumetric Inspect   Fabrication      printability check on the sampled grid
Volumetric Info      Utilities        what is installed
==================== ================ ==========================================

**Volumetric Mesh** needs a box: the window the model is cut to. Keep the
resolution modest; handing triangles to Rhino costs more than making them.
Export final parts headless.

Processes
=========

============================= ===================================================
Component                     Does
============================= ===================================================
Volumetric Abrasion           edges wear first
Volumetric Differential       soft rock retreats, hard rock stands proud
Volumetric Pitting            hollows that deepen themselves
Volumetric Strata             hard and soft beds weather into ledges
Volumetric Runoff             rain cuts gullies downhill
Volumetric Jointing           the mass splits into blocks
Volumetric Fingering          growth that folds into lobes
Volumetric Accretion          growth that fills hollows
Volumetric Branching          a tapering network, by space colonization
Volumetric Spinodal           a bicontinuous foam
Volumetric Reaction Diffusion Gray-Scott spots, worms and labyrinths
Volumetric Morphology         minimum feature size: open or close
============================= ===================================================

Each takes ``bounds`` and ``resolution`` like **Volumetric Mesh**, and returns a
:class:`~compas_vol.primitives.VolGrid` plus its ``history``.

* **To chain processes, leave** ``bounds`` **unwired downstream**: the
  component then runs on the incoming grid, without resampling. Mesh and
  Inspect read the box off a grid the same way. Branching, Spinodal and
  Reaction Diffusion need a box.
* **Use** ``run``. Each process takes 1-5 s at resolution 64 and reruns on
  every input change. Set ``run`` to ``False`` with a Boolean Toggle to hold
  the last result while adjusting upstream; unwired, it runs.

From canvas to script
=====================

A definition can be rewritten node for node and run headless, at resolutions
Grasshopper could not draw:

.. code-block:: python

    from compas_vol import nodes
    from compas_vol.meshing import write_stl

    body = nodes.boolean([nodes.box(None, 40.0, None, None, 4.0), nodes.sphere(None, 26.0)], "intersection", 2.0)
    body = nodes.boolean([body, nodes.tpms("Gyroid", 8.0, 1.2, None, None)], "intersection", 0)
    vertices, faces = nodes.mesh(body, 22.0, 400, 0)
    write_stl("part.stl", vertices, faces)
