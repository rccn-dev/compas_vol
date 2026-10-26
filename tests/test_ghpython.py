"""Checks on the Grasshopper component bundles.

A component only really runs inside Rhino, so nothing here can execute one.
What it can do is catch everything that would make the build fail or the
component lie: a missing file, a type hint the componentizer does not know,
or -- the one that actually bites -- inputs whose names have drifted apart
between ``metadata.json``, ``RunScript``, the docstring Grasshopper shows as a
tooltip, and the :mod:`compas_vol.nodes` function the component wraps.

What a component *does* is tested by calling its node, which is the reason
the nodes exist.

The rules encoded here mirror ``componentize_cpy.py`` in
``compas-dev/compas-actions.ghpython_components``.
"""

import ast
import json
import os
import struct

import pytest

COMPONENTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "compas_vol",
    "ghpython",
    "components",
)

#: Type hints the componentizer maps to a Grasshopper GUID. Anything else
#: aborts the build.
TYPE_HINTS = {
    "none", "ghdoc", "float", "bool", "int", "complex", "str", "datetime",
    "guid", "color", "point", "vector", "plane", "interval", "uvinterval",
    "box", "transform", "line", "circle", "arc", "polyline", "rectangle",
    "curve", "mesh", "surface", "subd", "brep", "pointcloud", "geometrybase",
}
EXPOSURE = {-1, 2, 4, 8, 16, 32, 64, 128}
ACCESS = {"item", "list", "tree", 0, 1, 2}
ICON_SIZE = 24


def component_names():
    return sorted(d for d in os.listdir(COMPONENTS) if os.path.isdir(os.path.join(COMPONENTS, d)))


@pytest.fixture(params=component_names())
def bundle(request):
    """The three files of one component, already parsed."""
    folder = os.path.join(COMPONENTS, request.param)
    with open(os.path.join(folder, "metadata.json")) as f:
        metadata = json.load(f)
    with open(os.path.join(folder, "code.py")) as f:
        code = f.read()
    return request.param, folder, metadata, code


def test_there_are_components():
    assert component_names(), "no component folders found in {}".format(COMPONENTS)


def test_files_present(bundle):
    _, folder, _, _ = bundle
    for filename in ("code.py", "metadata.json", "icon.png"):
        assert os.path.exists(os.path.join(folder, filename)), "{} is missing".format(filename)


def test_icon_is_24x24_png(bundle):
    """The componentizer embeds the icon as-is; Grasshopper draws it at 24x24."""
    _, folder, _, _ = bundle
    with open(os.path.join(folder, "icon.png"), "rb") as f:
        header = f.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", header[16:24])
    assert (width, height) == (ICON_SIZE, ICON_SIZE)


def test_metadata_fields(bundle):
    name, _, metadata, _ = bundle
    for key in ("name", "nickname", "category", "subcategory", "description", "instanceGuid"):
        assert metadata.get(key), "{} has no {}".format(name, key)
    assert metadata["exposure"] in EXPOSURE
    assert metadata["category"] == "COMPAS Vol", "all components share one toolbar tab"


def test_instance_guids_are_unique():
    """A repeated GUID makes Grasshopper treat two components as the same one."""
    seen = {}
    for name in component_names():
        with open(os.path.join(COMPONENTS, name, "metadata.json")) as f:
            guid = json.load(f)["instanceGuid"]
        assert guid not in seen, "{} and {} share an instanceGuid".format(name, seen.get(guid))
        seen[guid] = name


def test_parameters_are_valid(bundle):
    name, _, metadata, _ = bundle
    ghpython = metadata["ghpython"]
    assert ghpython.get("inputParameters") is not None
    assert ghpython.get("outputParameters"), "{} returns nothing".format(name)
    for param in ghpython["inputParameters"]:
        assert param.get("description"), "input {} of {} has no tooltip".format(param["name"], name)
        if "typeHintID" in param:
            assert param["typeHintID"] in TYPE_HINTS
        if "scriptParamAccess" in param:
            assert param["scriptParamAccess"] in ACCESS
    for param in ghpython["outputParameters"]:
        assert param.get("description"), "output {} of {} has no tooltip".format(param["name"], name)


def _run_script(code):
    """The single ``RunScript`` method defined in a component's source."""
    tree = ast.parse(code)
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert len(classes) == 1, "a component defines exactly one class"
    methods = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name == "RunScript"]
    assert len(methods) == 1, "a component defines exactly one RunScript"
    return tree, classes[0], methods[0]


def test_code_parses_and_defines_a_component(bundle):
    name, _, _, code = bundle
    tree, klass, _ = _run_script(code)
    bases = [b.id for b in klass.bases if isinstance(b, ast.Name)]
    assert bases == ["component"], "{} must subclass the componentbase alias".format(name)
    assert ast.get_docstring(tree), "{} has no module docstring, which is its Grasshopper help".format(name)


def test_runscript_arguments_match_metadata(bundle):
    """The names and order in metadata.json are what Grasshopper binds to.

    If they drift from RunScript's signature, the component still builds and
    then silently passes the wrong value to the wrong argument.
    """
    name, _, metadata, code = bundle
    _, _, method = _run_script(code)
    arguments = [a.arg for a in method.args.args][1:]  # drop self
    declared = [p["name"] for p in metadata["ghpython"]["inputParameters"]]
    assert arguments == declared, "{}: RunScript takes {}, metadata declares {}".format(name, arguments, declared)


def test_docstring_documents_every_parameter(bundle):
    """The module docstring is the tooltip, so it has to list what is really there."""
    name, _, metadata, code = bundle
    docstring = ast.get_docstring(ast.parse(code))
    for param in metadata["ghpython"]["inputParameters"]:
        assert "{}:".format(param["name"]) in docstring, "{} does not document input {}".format(name, param["name"])
    for param in metadata["ghpython"]["outputParameters"]:
        assert "{}:".format(param["name"]) in docstring, "{} does not document output {}".format(name, param["name"])


def _node_name(folder):
    """``Cv_Box`` wraps :func:`compas_vol.nodes.box`."""
    return folder[len("Cv_"):].lower()


def test_component_wraps_its_node(bundle):
    """A component is thin when it is a call to its node and nothing else.

    The node takes the component's inputs by the same names in the same order,
    so a script can be written from a canvas by reading the wires off.
    """
    import inspect

    from compas_vol import nodes

    name, _, metadata, code = bundle
    node = _node_name(name)
    assert node in nodes.__all__, "{} has no compas_vol.nodes.{}".format(name, node)
    declared = [p["name"] for p in metadata["ghpython"]["inputParameters"]]
    assert list(inspect.signature(getattr(nodes, node)).parameters) == declared
    _, _, method = _run_script(code)
    calls = [
        n for n in ast.walk(method)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "nodes"
    ]
    assert [c.func.attr for c in calls] == [node], "{} must call nodes.{} exactly once".format(name, node)


def test_node_returns_as_many_values_as_the_component_declares():
    """Run every node headless, with every input unwired, and count outputs."""
    from compas_vol import nodes

    for name in component_names():
        with open(os.path.join(COMPONENTS, name, "metadata.json")) as f:
            metadata = json.load(f)
        node = getattr(nodes, _node_name(name))
        result = node(*[None] * len(metadata["ghpython"]["inputParameters"]))
        expected = len(metadata["ghpython"]["outputParameters"])
        if name == "Cv_Mesh":
            expected = 2  # vertices and faces; the component turns them into (mesh, seconds)
        got = len(result) if isinstance(result, tuple) else 1
        assert got == expected, "nodes.{} returns {} value(s), {} declares {}".format(
            _node_name(name), got, name, expected
        )


def test_returns_as_many_values_as_declared(bundle):
    """Grasshopper unpacks the returned tuple positionally into the outputs."""
    name, _, metadata, code = bundle
    _, _, method = _run_script(code)
    expected = len(metadata["ghpython"]["outputParameters"])
    for node in ast.walk(method):
        if isinstance(node, ast.Return) and node.value is not None:
            if isinstance(node.value, ast.Call):
                continue  # passes the node's result through; checked against the node above
            got = len(node.value.elts) if isinstance(node.value, ast.Tuple) else 1
            assert got == expected, "{}: returns {} value(s), declares {} output(s)".format(name, got, expected)


def test_code_imports_what_rhino_annotates_with(bundle):
    """Rhino 8 rewrites RunScript with annotations taken from the inputs' types.

    A point input becomes ``point: Rhino.Geometry.Point3d``, a list input
    ``System.Collections.Generic.List[object]``, and the annotations are
    evaluated when the class is defined. Without these imports the class
    cannot be built, and Grasshopper reports only "Error getting
    GH_ScriptInstance instance" -- for every component whose inputs are typed
    as Rhino geometry or lists, while the rest work.
    """
    name, _, _, code = bundle
    imported = {
        alias.name
        for node in ast.parse(code).body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert {"Rhino", "System"} <= imported, "{} must import Rhino and System at module level".format(name)


def test_code_is_python_39_compatible(bundle):
    """Rhino 8 embeds CPython 3.9; anything newer will not even parse there.

    ``feature_version`` makes the check real on a newer interpreter: without
    it this would accept match statements and ``X | None`` annotations, and
    the component would only fail once it was in front of a designer.
    """
    _, _, _, code = bundle
    ast.parse(code, feature_version=(3, 9))


# ==============================================================================
# the adapter itself, which is ordinary Python and so can be tested here
# ==============================================================================


class _Point(object):
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class _BoundingBox(object):
    def __init__(self, lo, hi):
        self.Min, self.Max = _Point(*lo), _Point(*hi)


class _Plane(object):
    """Stands in for ``Rhino.Geometry.Plane``."""

    def __init__(self, origin, xaxis, yaxis):
        self.Origin, self.XAxis, self.YAxis = _Point(*origin), _Point(*xaxis), _Point(*yaxis)


class _Box(object):
    """Stands in for ``Rhino.Geometry.Box``, which exposes ``BoundingBox``."""

    def __init__(self, lo, hi):
        self.BoundingBox = _BoundingBox(lo, hi)


class _Brep(object):
    """Stands in for geometry that only answers ``GetBoundingBox``."""

    def __init__(self, lo, hi):
        self._bbox = _BoundingBox(lo, hi)

    def GetBoundingBox(self, accurate):
        return self._bbox


def test_point_to_compas():
    from compas_vol.ghpython import point_to_compas

    assert point_to_compas(None) is None
    assert list(point_to_compas(_Point(1, 2, 3))) == [1, 2, 3]


def test_plane_to_frame():
    from compas_vol.ghpython import plane_to_frame

    assert plane_to_frame(None) is None
    frame = plane_to_frame(_Plane((1, 2, 3), (0, 1, 0), (-1, 0, 0)))
    assert list(frame.point) == [1, 2, 3]
    assert list(frame.zaxis) == pytest.approx([0, 0, 1])


def test_box_component_chain_runs_headless():
    """What Cv_Box does with a Rhino plane, minus Grasshopper."""
    from compas_vol import nodes
    from compas_vol.ghpython import plane_to_frame

    vol = nodes.box(plane_to_frame(_Plane((10, 0, 0), (1, 0, 0), (0, 1, 0))), 4.0, None, None, 0)
    assert vol.get_distance([10, 0, 0]) == pytest.approx(-2.0)


def test_box_to_bounds_reads_a_box():
    from compas_vol.ghpython import box_to_bounds

    assert box_to_bounds(_Box((-1, -2, -3), (4, 5, 6))) == (-1, -2, -3, 4, 5, 6)


def test_box_to_bounds_reads_any_geometry():
    from compas_vol.ghpython import box_to_bounds

    assert box_to_bounds(_Brep((0, 0, 0), (10, 10, 10))) == (0, 0, 0, 10, 10, 10)


def test_box_to_bounds_result_is_accepted_by_the_sampler():
    """The whole point of the conversion: what comes out goes straight in."""
    from compas_vol.meshing import normalize_bounds
    from compas_vol.ghpython import box_to_bounds

    bounds = box_to_bounds(_Box((-5, -5, -5), (5, 5, 5)))
    assert normalize_bounds(bounds) == (-5, -5, -5, 5, 5, 5)


def test_mesh_to_rhino_passes_nothing_through():
    from compas_vol.ghpython import mesh_to_rhino

    assert mesh_to_rhino(None, None) is None


def test_to_rhino_mesh_says_what_is_missing_outside_rhino():
    from compas.geometry import Sphere
    from compas_vol.ghpython import to_rhino_mesh
    from compas_vol.primitives import VolSphere
    from compas_vol.runtime import context

    if context() == "rhino":  # pragma: no cover - only inside Rhino
        pytest.skip("Rhino is present, so there is nothing to fail on")
    with pytest.raises(ImportError) as error:
        to_rhino_mesh(VolSphere(Sphere(5.0)), _Box((-8, -8, -8), (8, 8, 8)), 16)
    assert "Rhino" in str(error.value)


def test_vector_to_compas():
    from compas_vol.ghpython import vector_to_compas

    assert vector_to_compas(None) is None
    assert list(vector_to_compas(_Point(0, 1, 2))) == [0, 1, 2]


# ==============================================================================
# the process components, run headless at a resolution small enough for CI
# ==============================================================================

#: Every process node, with small parameters so each runs in well under a
#: second. Inputs left as None fall back to the library's defaults, which is
#: also what an unwired input does on the canvas.
PROCESS_CASES = {
    "abrasion": lambda nodes, body, b, r, run=None: nodes.abrasion(body, b, r, 2.0, None, None, run=run),
    "differential": lambda nodes, body, b, r, run=None: nodes.differential(body, b, r, 2.0, 10.0, 1, run=run),
    "pitting": lambda nodes, body, b, r, run=None: nodes.pitting(body, b, r, 3.0, None, None, None, 10.0, 1, run=run),
    "strata": lambda nodes, body, b, r, run=None: nodes.strata(body, b, r, 5.0, None, 2.0, None, 1, run=run),
    "runoff": lambda nodes, body, b, r, run=None: nodes.runoff(body, b, r, 2.0, None, None, None, run=run),
    "jointing": lambda nodes, body, b, r, run=None: nodes.jointing(body, b, r, 6, 2.0, None, 1, None, run=run),
    "fingering": lambda nodes, body, b, r, run=None: nodes.fingering(body, b, r, 3.0, None, None, None, run=run),
    "accretion": lambda nodes, body, b, r, run=None: nodes.accretion(body, b, r, 2.0, None, None, run=run),
    "branching": lambda nodes, body, b, r, run=None: nodes.branching(
        (-20, -20, 0, 20, 20, 40), r, None, 200, None, None, None, None, 1, run=run
    ),
    "spinodal": lambda nodes, body, b, r, run=None: nodes.spinodal(20.0, r, 6.0, None, 60, 0, run=run),
    "reactiondiffusion": lambda nodes, body, b, r, run=None: nodes.reactiondiffusion(
        20.0, r, None, None, 300, None, 0, run=run
    ),
    "morphology": lambda nodes, body, b, r, run=None: nodes.morphology(body, b, r, "open", 2.0, run=run),
}


@pytest.fixture
def processes_extra():
    pytest.importorskip("skfmm", reason="needs the processes extra")


def test_every_process_component_has_a_case():
    process_components = []
    for name in component_names():
        with open(os.path.join(COMPONENTS, name, "metadata.json")) as f:
            if json.load(f)["subcategory"] == "Processes":
                process_components.append(_node_name(name))
    assert sorted(process_components) == sorted(PROCESS_CASES)


@pytest.mark.parametrize("name", sorted(PROCESS_CASES))
def test_process_node_returns_a_grid_and_its_history(processes_extra, name):
    from compas_vol import nodes
    from compas_vol.primitives import VolGrid

    body = nodes.box(None, 30.0, None, None, 0)
    result, history = PROCESS_CASES[name](nodes, body, 22.0, 24)
    assert isinstance(result, VolGrid)
    assert result.values.shape == (24, 24, 24)
    assert result.values.min() < 0 < result.values.max()
    last = {"morphology": "opened", "reactiondiffusion": "reaction_diffusion"}.get(name, name)
    assert history.splitlines()[-1].startswith(last + "(")


def test_processes_chain_on_the_grid_without_resampling(processes_extra):
    """A grid with no bounds runs where it is; the history carries both steps."""
    from compas_vol import nodes

    worn, _ = nodes.abrasion(nodes.box(None, 30.0, None, None, 0), 22.0, 24, 2.0, None, None)
    pitted, history = nodes.pitting(worn, None, None, 3.0, None, None, None, 10.0, 1)
    assert (pitted.origin, pitted.spacing, pitted.values.shape) == (worn.origin, worn.spacing, worn.values.shape)
    steps = [line.split("(")[0] for line in history.splitlines()]
    assert steps.index("abrasion") < steps.index("pitting")


def test_process_needs_bounds_for_anything_but_a_grid():
    """Like the Mesh component: a field has no extent until it is given one."""
    from compas_vol import nodes

    assert nodes.abrasion(nodes.sphere(None, 5.0), None, None, None, None, None) == (None, None)
    assert nodes.spinodal(None, None, None, None, None, None) == (None, None)


def test_mesh_and_inspect_read_the_domain_off_a_grid():
    pytest.importorskip("skimage", reason="needs the meshing extra")
    import numpy as np

    from compas_vol import nodes
    from compas_vol.primitives import VolGrid

    x, y, z = np.ogrid[-10:10:21j, -10:10:21j, -10:10:21j]
    ball = VolGrid(np.sqrt(x**2 + y**2 + z**2) - 6.0, (-10, -10, -10), (1, 1, 1))
    vertices, faces = nodes.mesh(ball, None, None, 0)
    assert len(faces) and np.abs(np.linalg.norm(vertices, axis=1) - 6.0).max() < 0.2
    _, ok, pieces = nodes.inspect(ball, None, None, None, None)
    assert pieces == 1


def test_strata_refuses_vertical_beds(processes_extra):
    from compas.geometry import Vector

    from compas_vol import nodes

    with pytest.raises(ValueError, match="horizontal"):
        nodes.strata(nodes.box(None, 30.0, None, None, 0), 22.0, 16, None, Vector(1, 0, 0), None, None, None)


def test_strata_normal_sets_the_dip(processes_extra):
    from compas.geometry import Vector

    from compas_vol import nodes

    _, history = nodes.strata(nodes.box(None, 30.0, None, None, 0), 22.0, 16, None, Vector(1, 0, 2), None, 0, 0)
    assert "dip=(0.5, 0.0)" in history


def test_morphology_names_its_operations():
    from compas_vol import nodes

    with pytest.raises(ValueError, match="open or close"):
        nodes.morphology(nodes.sphere(None, 5.0), 8.0, 16, "erode", 1.0)


def test_process_components_end_with_a_run_toggle():
    for name in component_names():
        with open(os.path.join(COMPONENTS, name, "metadata.json")) as f:
            metadata = json.load(f)
        if metadata["subcategory"] != "Processes":
            continue
        last = metadata["ghpython"]["inputParameters"][-1]
        assert (last["name"], last.get("typeHintID")) == ("run", "bool"), name


@pytest.mark.parametrize("name", sorted(PROCESS_CASES))
def test_process_node_does_nothing_when_run_is_off(name):
    """Headless there is nothing to hold, so run=False returns nothing at all."""
    from compas_vol import nodes

    body = nodes.box(None, 30.0, None, None, 0)
    assert PROCESS_CASES[name](nodes, body, 22.0, 24, run=False) == (None, None)
