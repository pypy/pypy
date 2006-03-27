"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.translator.cli.options import getoption

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

def lltype_to_cts(t):
    try:
        return _lltype_to_cts[t]
    except KeyError:
        if getoption('nostop'):
            log.WARNING('Unknown type %s' % t)
            return t
        else:
            assert False, 'Unknown type %s' % t

def lltype_to_ilasm(t):
    return ctstype_to_ilasm(lltype_to_cts(t))

def ctstype_to_ilasm(t):
    try:
        return _cts_to_ilasm[t]
    except KeyError:
        if getoption('nostop'):
            log.WARNING('Unknown ilasm type %s' % t)
            return t
        else:
            assert False, 'Unknown ilasm type %s' % t


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
