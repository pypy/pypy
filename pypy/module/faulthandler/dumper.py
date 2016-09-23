from rpython.rtyper.annlowlevel import llstr
from rpython.rlib import rgc
from rpython.rlib.rvmprof import enum_all_code_objs
from rpython.rlib.rvmprof import cintf as rvmprof_cintf

from pypy.interpreter.pycode import PyCode
from pypy.module.faulthandler.cintf import pypy_faulthandler_write
from pypy.module.faulthandler.cintf import pypy_faulthandler_write_int

#
# xxx The dumper is tied to the internals of rvmprof. xxx
#


MAX_FRAME_DEPTH = 100


def _dump(s):
    pypy_faulthandler_write(llstr(s))

def _dump_int(i):
    pypy_faulthandler_write_int(i)


def dump_code(pycode, this_code_id, search_code_id):
    if this_code_id != search_code_id:
        return 0
    _dump('"')
    _dump(pycode.co_filename)
    _dump('" in ')
    _dump(pycode.co_name)
    _dump(" (starting at line ")
    _dump_int(pycode.co_firstlineno)
    _dump(")\n")
    return 1


@rgc.no_collect
def _dump_callback():
    """We are as careful as we can reasonably be here (i.e. not 100%,
    but hopefully close enough).  In particular, this is written as
    RPython but shouldn't allocate anything.
    """
    _dump("Stack (most recent call first):\n")

    s = rvmprof_cintf.get_rvmprof_stack()
    depth = 0
    while s:
        if depth >= MAX_FRAME_DEPTH:
            _dump("  ...\n")
            break
        if s.c_kind == rvmprof_cintf.VMPROF_CODE_TAG:
            code_id = s.c_value
            _dump("  File ")
            if enum_all_code_objs(PyCode, dump_code, code_id) == 0:
                _dump("???\n")
        s = s.c_next
        depth += 1
