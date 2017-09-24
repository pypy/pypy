from pypy.interpreter.generator import GeneratorIterator, Coroutine
from pypy.module.cpyext.api import (
    build_type_checkers, cts, parse_dir, bootstrap_function)
from pypy.module.cpyext.pyobject import make_typedescr, as_pyobj
from pypy.module.cpyext.object import _dealloc

cts.parse_header(parse_dir / 'cpyext_genobject.h')

@bootstrap_function
def init_genobject(space):
    make_typedescr(GeneratorIterator.typedef,
                   basestruct=cts.gettype('PyGenObject'),
                   attach=gi_attach,
                   dealloc=_dealloc)


PyGen_Check, PyGen_CheckExact = build_type_checkers("Gen", GeneratorIterator)

_, PyCoro_CheckExact = build_type_checkers("Coro", Coroutine)

def gi_attach(space, py_obj, w_obj, w_userdata=None):
    py_obj.c_gi_code = as_pyobj(space, w_obj.pycode)

def gi_realize(space, py_obj):
    raise NotImplementedError(
        "PyPy doesn't support creation of generators from the C-API.")

def gi_dealloc(space, py_obj):
    _dealloc(space, py_obj)
