from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter.astcompiler import ast, consts


class Module(MixedModule):

    interpleveldefs = {
        "PyCF_ONLY_AST" : "space.wrap(%s)" % consts.PyCF_ONLY_AST,
        "PyCF_ACCEPT_NULL_BYTES":
                          "space.wrap(%s)" % consts.PyCF_ACCEPT_NULL_BYTES,
        "__version__"   : "space.wrap('82160')",  # from CPython's svn.
        }
    appleveldefs = {}


def _setup():
    defs = Module.interpleveldefs
    defs['AST'] = "pypy.interpreter.astcompiler.ast.get(space).w_AST"
    for (name, base, fields, attributes) in ast.State.AST_TYPES:
        defs[name] = "pypy.interpreter.astcompiler.ast.get(space).w_" + name
_setup()
