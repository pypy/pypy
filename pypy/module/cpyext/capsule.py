from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module.cpyext.api import (PyObjectFields, bootstrap_function,
    cpython_api, cpython_struct, PyObject, build_type_checkers, cts, parse_dir)
from pypy.module.cpyext.pyobject import (
    make_typedescr, track_reference, from_ref)
from pypy.interpreter.error import oefmt

cts.parse_header(parse_dir / 'cpyext_capsule.h')

PyCapsule_Check, PyCasule_CheckExact = build_type_checkers("Capsule")
