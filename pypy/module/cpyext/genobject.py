from pypy.interpreter.generator import GeneratorIterator, Coroutine
from pypy.module.cpyext.api import build_type_checkers


PyGen_Check, PyGen_CheckExact = build_type_checkers("Gen", GeneratorIterator)

_, PyCoro_CheckExact = build_type_checkers("Coro", Coroutine)
