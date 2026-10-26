********************************************************************************
Development
********************************************************************************

Tests and docs
==============

.. code-block:: bash

    uv sync --extra meshing --group dev
    uv run python -m pytest                     # the suite, with doctests
    uv run ruff check .
    uv sync --group docs && uv run sphinx-build -b html -W docs docs/_build/html

Every volumetric class runs through shared checks: the two distance methods
agree, queries do not mutate their input, and objects survive a JSON round
trip. Analytic cases pin the geometry (a radius-5 sphere has mean curvature
0.2). Bug fixes get a regression test in ``tests/test_regressions.py``.
``tests/test_examples.py`` keeps the examples parsing and importing.

Building the components
=======================

Each component is a folder under ``src/compas_vol/ghpython/components``:
``code.py``, ``metadata.json`` and a 24x24 ``icon.png``, drawn from a text
sketch by ``scripts/make_icons.py``. ``scripts/ghuser`` compiles them into
``.ghuser`` files with `ghuser-builder
<https://git.rccn.dev/libs/ghuser-builder>`_, cloned next to this repository or
wherever ``GHUSER_BUILDER`` points:

.. code-block:: bash

    scripts/ghuser dev             # Mac with Rhino 8: build, link into Grasshopper, check, reload
    scripts/ghuser dev status      # what Grasshopper will load, and what is wrong
    scripts/ghuser dev uninstall
    scripts/ghuser                 # Docker, as CI: dist/ghuser/, with icons

``dev`` is the everyday loop:

#. It builds with Rhino's own .NET, adds ``# env: <checkout>/src`` so
   components import the working copy, and verifies every file.
#. It links ``build/ghuser-dev`` into Grasshopper's User Object folder as
   ``compas_vol-dev``. Older copies of the same components move to
   ``~/.cache/ghuser-builder/backups``.
#. It checks the ``# r:`` requirements and ``import compas_vol`` in Rhino's
   Python.
#. If Rhino is running, it reloads ``compas_vol`` there and lists components
   on the canvas that carry older code. New components appear after
   restarting Grasshopper.

Rebuild when a ``code.py`` or ``metadata.json`` changes; library edits need
only a recompute. Dev builds have no canvas icon (a macOS limitation) and only
work on this machine. Both build paths read every file back with ``GH_IO`` and
compare it with its source.

Adding a component
==================

#. Add ``something(...)`` to :mod:`compas_vol.nodes`, taking the component's
   inputs by name and returning COMPAS or NumPy types.
#. Add ``components/Cv_Something/`` with ``code.py`` (convert, call
   ``nodes.something``, convert back) and ``metadata.json``.
#. Keep ``import System`` and ``import Rhino`` at the top of ``code.py``.
   Rhino 8 evaluates the input type annotations it adds to ``RunScript``;
   without them Grasshopper reports *Error getting GH_ScriptInstance
   instance*.
#. Give it a fresh ``instanceGuid``: two components with one GUID are one
   component to Grasshopper.
#. Add a 12x12 sketch to ``scripts/make_icons.py`` and run it.
#. Run ``pytest tests/test_ghpython.py``. It checks that input names agree
   across ``metadata.json``, ``RunScript``, the node and the tooltip.
