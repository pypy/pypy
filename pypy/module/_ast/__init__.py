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
    for name, cls in ast.__dict__.iteritems():
        if isinstance(cls, type) and issubclass(cls, ast.AST):
            defs[name.lstrip("_")] = cls.__module__ + "." + name
_setup()
