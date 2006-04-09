"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.ootypesystem.ootype import Instance, Class, StaticMethod
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
    Class: 'class [mscorlib]System.Type',
    }

_pyexception_to_cts = {
    exceptions.Exception: '[mscorlib]System.Exception',
    exceptions.OverflowError: '[mscorlib]System.OverflowException'
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

class CTS(object):
    def __init__(self, db):
        self.db = db

    def lltype_to_cts(self, t):
        if isinstance(t, Instance):
            name = t._name
            self.db.pending_class(t)
            return 'class %s' % name
        elif isinstance(t, StaticMethod):
            return 'void' # TODO: is it correct to ignore StaticMethod?

        return _get_from_dict(_lltype_to_cts, t, 'Unknown type %s' % t)

    def llvar_to_cts(self, var):
        return self.lltype_to_cts(var.concretetype), var.name

    def llconst_to_cts(self, const):
        return self.lltype_to_cts(const.concretetype), const.value

    def graph_to_signature(self, graph, is_method = False, func_name = None):
        ret_type, ret_var = self.llvar_to_cts(graph.getreturnvar())
        func_name = func_name or graph.name

        args = graph.getargs()
        if is_method:
            args = args[1:]

        arg_types = [self.lltype_to_cts(arg.concretetype) for arg in args]
        arg_list = ', '.join(arg_types)

        return '%s %s(%s)' % (ret_type, func_name, arg_list)

    def split_class_name(self, class_name):
        parts = class_name.rsplit('.', 1)
        if len(parts) == 2:
            return parts
        else:
            return None, parts[0]

    def pyexception_to_cts(self, exc):
        return _get_from_dict(_pyexception_to_cts, exc, 'Unknown exception %s' % exc)
