"""
This file defines utilities for manipulating the stack in an
RPython-compliant way, intended mostly for use by the Stackless PyPy.
"""

import inspect

from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib import rgc
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.controllerentry import Controller, SomeControlledInstance
from pypy.translator.tool.cbuild import ExternalCompilationInfo

# ____________________________________________________________

compilation_info = ExternalCompilationInfo(includes=['src/stack.h'])

def llexternal(name, args, res, _callable=None):
    return rffi.llexternal(name, args, res, compilation_info=compilation_info,
                           sandboxsafe=True, _nowrapper=True,
                           _callable=_callable)

_stack_get_end = llexternal('LL_stack_get_end', [], lltype.Signed,
                            lambda: 0)
_stack_get_length = llexternal('LL_stack_get_length', [], lltype.Signed,
                               lambda: 1)
_stack_set_length_fraction = llexternal('LL_stack_set_length_fraction',
                                        [lltype.Float], lltype.Void,
                                        lambda frac: None)
_stack_too_big_slowpath = llexternal('LL_stack_too_big_slowpath',
                                     [lltype.Signed], lltype.Char,
                                     lambda cur: '\x00')
# the following is used by the JIT
_stack_get_end_adr   = llexternal('LL_stack_get_end_adr',   [], lltype.Signed)
_stack_get_length_adr= llexternal('LL_stack_get_length_adr',[], lltype.Signed)

# the following is also used by the JIT: "critical code" paths are paths in
# which we should not raise StackOverflow at all, but just ignore the stack limit
_stack_criticalcode_start = llexternal('LL_stack_criticalcode_start', [],
                                       lltype.Void, lambda: None)
_stack_criticalcode_stop = llexternal('LL_stack_criticalcode_stop', [],
                                      lltype.Void, lambda: None)

def stack_check():
    if not we_are_translated():
        return
    #
    # Load the "current" stack position, or at least some address that
    # points close to the current stack head
    current = llop.stack_current(lltype.Signed)
    #
    # Load these variables from C code
    end = _stack_get_end()
    length = _stack_get_length()
    #
    # Common case: if 'current' is within [end-length:end], everything
    # is fine
    ofs = r_uint(end - current)
    if ofs <= r_uint(length):
        return
    #
    # Else call the slow path
    stack_check_slowpath(current)
stack_check._always_inline_ = True

@rgc.no_collect
def stack_check_slowpath(current):
    if ord(_stack_too_big_slowpath(current)):
        from pypy.rlib.rstackovf import _StackOverflow
        raise _StackOverflow
stack_check_slowpath._dont_inline_ = True
