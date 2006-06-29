"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.option import getoption
from pypy.translator.cli import oopspec

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

PYPY_LIST = '[pypylib]pypy.runtime.List`1<%s>'
PYPY_LIST_OF_VOID = '[pypylib]pypy.runtime.ListOfVoid'
PYPY_DICT = '[pypylib]pypy.runtime.Dict`2<%s, %s>'
PYPY_DICT_ITEMS_ITERATOR = '[pypylib]pypy.runtime.DictItemsIterator`2<%s, %s>'
PYPY_STRING_BUILDER = '[pypylib]pypy.runtime.StringBuilder'

_lltype_to_cts = {
    ootype.Void: 'void',
    ootype.Signed: 'int32',    
    ootype.Unsigned: 'unsigned int32',
    SignedLongLong: 'int64',
    UnsignedLongLong: 'unsigned int64',
    ootype.Bool: 'bool',
    ootype.Float: 'float64',
    ootype.Char: 'char',
    ootype.UniChar: 'char',
    ootype.Class: 'class [mscorlib]System.Type',
    ootype.String: 'string',
    ootype.StringBuilder: 'class ' + PYPY_STRING_BUILDER,

    # maps generic types to their ordinal
    ootype.List.SELFTYPE_T: 'class ' + (PYPY_LIST % '!0'),
    ootype.List.ITEMTYPE_T: '!0',
    ootype.Dict.SELFTYPE_T: 'class ' + (PYPY_DICT % ('!0', '!1')),
    ootype.Dict.KEYTYPE_T: '!0',
    ootype.Dict.VALUETYPE_T: '!1',
    ootype.DictItemsIterator.SELFTYPE_T: 'class ' + (PYPY_DICT_ITEMS_ITERATOR % ('!0', '!1')),
    ootype.DictItemsIterator.KEYTYPE_T: '!0',
    ootype.DictItemsIterator.VALUETYPE_T: '!1',
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
    ILASM_KEYWORDS = ['call', 'on', 'string']
    
    def __init__(self, db):
        self.db = db

    def __class(self, result, include_class):
        if include_class:
            return 'class ' + result
        else:
            return result

    def escape_name(self, name):
        """Mangle then name if it's a ilasm reserved word"""
        if name in self.ILASM_KEYWORDS:
            return name + '__MANGLED' # XXX: it could not be unique
        else:
            return name

    def lltype_to_cts(self, t, include_class=True):
        if isinstance(t, ootype.Instance):
            self.db.pending_class(t)
            return self.__class(t._name, include_class)
        elif isinstance(t, ootype.Record):
            name = self.db.pending_record(t)
            return self.__class(name, include_class)
        elif isinstance(t, ootype.StaticMethod):
            delegate = self.db.record_delegate_type(t)
            return self.__class(delegate, include_class)
        elif isinstance(t, ootype.List):
            item_type = self.lltype_to_cts(t._ITEMTYPE)
            if item_type == 'void': # special case: List of Void
                return self.__class(PYPY_LIST_OF_VOID, include_class)
            return self.__class(PYPY_LIST % item_type, include_class)
        elif isinstance(t, ootype.Dict):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            return self.__class(PYPY_DICT % (key_type, value_type), include_class)
        elif isinstance(t, ootype.DictItemsIterator):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            return self.__class(PYPY_DICT_ITEMS_ITERATOR % (key_type, value_type), include_class)

        return _get_from_dict(_lltype_to_cts, t, 'Unknown type %s' % t)

    def llvar_to_cts(self, var):
        return self.lltype_to_cts(var.concretetype), var.name

    def llconst_to_cts(self, const):
        return self.lltype_to_cts(const.concretetype), const.value

    def ctor_name(self, t):
        return 'instance void %s::.ctor()' % self.lltype_to_cts(t)

    def graph_to_signature(self, graph, is_method = False, func_name = None):
        ret_type, ret_var = self.llvar_to_cts(graph.getreturnvar())
        func_name = func_name or graph.name
        func_name = self.escape_name(func_name)

        args = [arg for arg in graph.getargs() if arg.concretetype is not ootype.Void]
        if is_method:
            args = args[1:]

        arg_types = [self.lltype_to_cts(arg.concretetype) for arg in args]
        arg_list = ', '.join(arg_types)

        return '%s %s(%s)' % (ret_type, func_name, arg_list)

    def method_signature(self, TYPE, name):
        # TODO: use callvirt only when strictly necessary
        if isinstance(TYPE, ootype.Instance):
            owner, meth = TYPE._lookup(name)
            class_name = TYPE._name
            full_name = 'class %s::%s' % (class_name, name)
            return self.graph_to_signature(meth.graph, True, full_name), True

        elif isinstance(TYPE, (ootype.BuiltinType, ootype.StaticMethod)):
            if isinstance(TYPE, ootype.StaticMethod):
                METH = TYPE
            else:
                METH = oopspec.get_method(TYPE, name)
            class_name = self.lltype_to_cts(TYPE)
            ret_type = self.lltype_to_cts(METH.RESULT)
            arg_types = [self.lltype_to_cts(arg) for arg in METH.ARGS if arg is not ootype.Void]
            arg_list = ', '.join(arg_types)
            return '%s %s::%s(%s)' % (ret_type, class_name, name, arg_list), False

        else:
            assert False

    def split_class_name(self, class_name):
        parts = class_name.rsplit('.', 1)
        if len(parts) == 2:
            return parts
        else:
            return None, parts[0]
