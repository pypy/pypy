from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.astcompiler import ast, consts


class Module(MixedModule):

    interpleveldefs = {
        "PyCF_ONLY_AST" : "space.wrap(%s)" % consts.PyCF_ONLY_AST,
        "__version__"   : "space.wrap('82160')",  # from CPython's svn.
        }
    appleveldefs = {}


def _setup():
    defs = Module.interpleveldefs
    for (name, base, fields) in ast.State.AST_TYPES:
        defs[name] = "pypy.interpreter.astcompiler.ast.get(space).w_" + name
_setup()
