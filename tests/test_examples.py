"""The examples are code too: they must parse, and import nothing compas_vol no longer has.

Running them opens a viewer, and several run simulations, so that is left to
whoever edits them. This catches the usual way an example rots without
running it: an API it uses has moved on.
"""

import ast
import importlib
import os

import pytest

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
EXAMPLES = sorted(f for f in os.listdir(FOLDER) if f.endswith(".py"))


def test_examples_are_numbered_in_reading_order():
    numbered = [f for f in EXAMPLES if f[:2].isdigit()]
    numbers = [int(f[:2]) for f in numbered]
    assert numbers == list(range(1, len(numbered) + 1)), "examples should be numbered 01, 02, ... without gaps"


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_parses(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8") as f:
        ast.parse(f.read(), feature_version=(3, 9))


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_imports_resolve(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "compas_vol":
            module = importlib.import_module(node.module)
            for alias in node.names:
                assert hasattr(module, alias.name), "{} imports {}.{}, which is gone".format(
                    name, node.module, alias.name)


def test_every_example_is_in_the_index():
    with open(os.path.join(FOLDER, "README.md"), encoding="utf-8") as f:
        index = f.read()
    missing = [name for name in EXAMPLES if name[:2].isdigit() and "`{}`".format(name) not in index]
    assert not missing, "not in examples/README.md: {}".format(missing)
