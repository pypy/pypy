"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.ootypesystem.ootype import Instance
from pypy.translator.cli.option import getoption

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 


_lltype_to_cts = {
    Void: 'void',
    Signed: 'int32',    
    Unsigned: 'unsigned int32',
    SignedLongLong: 'int64',
    UnsignedLongLong: 'unsigned int64',
    Bool: 'bool',
    Float: 'float64',
    }

_cts_to_ilasm = {
    'int32': 'i4',
    'unsigned int32': 'i4',
    'int64': 'i8',
    'unsigned int64': 'i8',
    'bool': 'i4',
    'float64': 'r8',
    }

def _get_from_dict(d, key, error):
    try:
        return d[key]
    except KeyError:
        if getoption('nostop'):
            log.WARNING(error)
            return key
        else:
            assert False, error


def lltype_to_cts(t):
    # TODO: handle instances more accurately
    if isinstance(t, Instance):
        return 'object'

    return _get_from_dict(_lltype_to_cts, t, 'Unknown type %s' % t)

def lltype_to_ilasm(t):
    return ctstype_to_ilasm(lltype_to_cts(t))

def ctstype_to_ilasm(t):
    return _get_from_dict(_cts_to_ilasm, t, 'Unknown ilasm type %s' % t)

def llvar_to_cts(var):
    return lltype_to_cts(var.concretetype), var.name

def llconst_to_cts(const):
    return lltype_to_cts(const.concretetype), const.value

def llconst_to_ilasm(const):
    """
    Return the const as a string suitable for ilasm.
    """
    ilasm_type = lltype_to_ilasm(const.concretetype)
    if const.concretetype is Bool:
        return ilasm_type, str(int(const.value))
    elif const.concretetype is Float:
        return ilasm_type, repr(const.value)
    else:
        return ilasm_type, str(const.value)

def graph_to_signature(graph):
    ret_type, ret_var = llvar_to_cts(graph.getreturnvar())
    func_name = graph.name
    arg_types = [lltype_to_cts(arg.concretetype) for arg in graph.getargs()]
    arg_list = ', '.join(arg_types)

    return '%s %s(%s)' % (ret_type, func_name, arg_list)

_pyexception_to_cts = {
    exceptions.Exception: '[mscorlib]System.Exception',
    exceptions.OverflowError: '[mscorlib]System.OverflowException'
    }

def pyexception_to_cts(exc):
    return _get_from_dict(_pyexception_to_cts, exc, 'Unknown exception %s' % exc)
