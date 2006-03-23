"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

from pypy.rpython.lltypesystem.lltype import Signed, Void, Bool
from pypy.translator.cli import conftest

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 


_lltype_to_cts = {
    Signed: 'int32',
    Void: 'void',
    Bool: 'bool',
    }

_cts_to_ilasm = {
    'int32': 'i4',
    'bool': 'i4'
    }

def lltype_to_cts(t):
    try:
        return _lltype_to_cts[t]
    except KeyError:
        if conftest.option.nostop:
            log.WARNING('Unknown type %s' % t)
            return t
        else:
            assert False, 'Unknown type %s' % t

def lltype_to_ilasm(t):
    try:
        return _cts_to_ilasm[lltype_to_cts(t)]
    except KeyError:
        if conftest.option.nostop:
            log.WARNING('Unknown ilasm type %s' % t)
            return t
        else:
            assert False, 'Unknown ilasm type %s' % t
    
def llvar_to_cts(var):
    return lltype_to_cts(var.concretetype), var.name

def llconst_to_cts(const):
    return lltype_to_cts(const.concretetype), const.value

def llconst_to_ilasm(const):
    ilasm_type = lltype_to_ilasm(const.concretetype)
    if const.concretetype is Bool:
        return ilasm_type, int(const.value)
    else:
        return ilasm_type, const.value

def graph_to_signature(graph):
    ret_type, ret_var = llvar_to_cts(graph.getreturnvar())
    func_name = graph.name
    arg_types = [lltype_to_cts(arg.concretetype) for arg in graph.getargs()]
    arg_list = ', '.join(arg_types)

    return '%s %s(%s)' % (ret_type, func_name, arg_list)
