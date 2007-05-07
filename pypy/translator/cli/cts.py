"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem.llmemory import WeakGcAddress
from pypy.translator.cli.option import getoption
from pypy.translator.cli import oopspec

try:
    set
except NameError:
    from sets import Set as set

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

WEAKREF = '[mscorlib]System.WeakReference'
PYPY_LIST = '[pypylib]pypy.runtime.List`1<%s>'
PYPY_LIST_OF_VOID = '[pypylib]pypy.runtime.ListOfVoid'
PYPY_DICT = '[pypylib]pypy.runtime.Dict`2<%s, %s>'
PYPY_DICT_OF_VOID = '[pypylib]pypy.runtime.DictOfVoid`2<%s, int32>'
PYPY_DICT_VOID_VOID = '[pypylib]pypy.runtime.DictVoidVoid'
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
    WeakGcAddress: 'class ' + WEAKREF,

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

    ILASM_KEYWORDS = set(["at", "as", "implicitcom", "implicitres",
    "noappdomain", "noprocess", "nomachine", "extern", "instance",
    "explicit", "default", "vararg", "unmanaged", "cdecl", "stdcall",
    "thiscall", "fastcall", "marshal", "in", "out", "opt", "retval",
    "static", "public", "private", "family", "initonly",
    "rtspecialname", "specialname", "assembly", "famandassem",
    "famorassem", "privatescope", "literal", "notserialized", "value",
    "not_in_gc_heap", "interface", "sealed", "abstract", "auto",
    "sequential", "ansi", "unicode", "autochar", "bestfit",
    "charmaperror", "import", "serializable", "nested", "lateinit",
    "extends", "implements", "final", "virtual", "hidebysig",
    "newslot", "unmanagedexp", "pinvokeimpl", "nomangle", "ole",
    "lasterr", "winapi", "native", "il", "cil", "optil", "managed",
    "forwardref", "runtime", "internalcall", "synchronized",
    "noinlining", "custom", "fixed", "sysstring", "array", "variant",
    "currency", "syschar", "void", "bool", "int8", "int16", "int32",
    "int64", "float32", "float64", "error", "unsigned", "uint",
    "uint8", "uint16", "uint32", "uint64", "decimal", "date", "bstr",
    "lpstr", "lpwstr", "lptstr", "objectref", "iunknown", "idispatch",
    "struct", "safearray", "int", "byvalstr", "tbstr", "lpvoid",
    "any", "float", "lpstruct", "null", "ptr", "vector", "hresult",
    "carray", "userdefined", "record", "filetime", "blob", "stream",
    "storage", "streamed_object", "stored_object", "blob_object",
    "cf", "clsid", "method", "class", "pinned", "modreq", "modopt",
    "typedref", "type","refany", "wchar", "char", "fromunmanaged",
    "callmostderived", "bytearray", "with", "init", "to", "catch",
    "filter", "finally", "fault", "handler", "tls", "field",
    "request", "demand", "assert", "deny", "permitonly", "linkcheck",
    "inheritcheck", "reqmin", "reqopt", "reqrefuse", "prejitgrant",
    "prejitdeny", "noncasdemand", "noncaslinkdemand",
    "noncasinheritance", "readonly", "nometadata", "algorithm",
    "fullorigin", "nan", "inf", "publickey", "enablejittracking",
    "disablejitoptimizer", "preservesig", "beforefieldinit",
    "alignment", "nullref", "valuetype", "compilercontrolled",
    "reqsecobj", "enum", "object", "string", "true", "false", "is",
    "on", "off", "add", "and", "arglist", "beq", "bge", "bgt", "ble",
    "blt", "bne", "box", "br", "break", "brfalse", "brnull", "brtrue",
    "call", "calli", "callvirt", "castclass", "ceq", "cgt",
    "ckfinite", "clt", "conf", "constrained", "conv", "cpblk",
    "cpobj", "div", "dup", "endfault", "endfilter", "endfinally",
    "initblk", "initobj", "isinst", "jmp", "ldarg", "ldarga", "ldc",
    "ldelem", "ldelema", "ldfld", "ldflda", "ldftn", "ldind", "ldlen",
    "ldloc", "ldloca", "ldnull", "ldobj", "ldsfld", "ldsflda",
    "ldstr", "ldtoken", "ldvirtftn", "leave", "localloc", "mkrefany",
    "mul", "neg", "newarr", "newobj", "nop", "not", "or", "pop",
    "readonly", "refanytype", "refanyval", "rem", "ret", "rethrow",
    "shl", "shr", "sizeof", "starg", "stelem", "stfld", "stind",
    "stloc", "stobj", "stsfld", "sub", "switch", "tail", "throw",
    "unaligned", "unbox", "volatile", "xor"])

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
            return "'%s'" % name
        else:
            return name

    def lltype_to_cts(self, t, include_class=True):
        if t is ootype.ROOT:
            return self.__class('[mscorlib]System.Object', include_class)
        elif isinstance(t, lltype.Ptr) and isinstance(t.TO, lltype.OpaqueType):
            return self.__class('[mscorlib]System.Object', include_class)
        elif isinstance(t, ootype.Instance):
            NATIVE_INSTANCE = t._hints.get('NATIVE_INSTANCE', None)
            if NATIVE_INSTANCE:
                return self.__class(NATIVE_INSTANCE._name, include_class)
            else:
                name = self.db.pending_class(t)
                return self.__class(name, include_class)
        elif isinstance(t, ootype.Record):
            name = self.db.pending_record(t)
            return self.__class(name, include_class)
        elif isinstance(t, ootype.StaticMethod):
            delegate = self.db.record_delegate(t)
            return self.__class(delegate, include_class)
        elif isinstance(t, ootype.List):
            item_type = self.lltype_to_cts(t._ITEMTYPE)
            if item_type == 'void': # special case: List of Void
                return self.__class(PYPY_LIST_OF_VOID, include_class)
            return self.__class(PYPY_LIST % item_type, include_class)
        elif isinstance(t, ootype.Dict):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            if value_type == 'void': # special cases: Dict with voids
                if key_type == 'void':
                    return self.__class(PYPY_DICT_VOID_VOID, include_class)
                else:
                    return self.__class(PYPY_DICT_OF_VOID % key_type, include_class)
            return self.__class(PYPY_DICT % (key_type, value_type), include_class)
        elif isinstance(t, ootype.DictItemsIterator):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            if key_type == 'void':
                key_type = 'int32' # placeholder
            if value_type == 'void':
                value_type = 'int32' # placeholder
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
        namespace = getattr(graph.func, '_namespace_', None)
        if namespace:
            func_name = '%s::%s' % (namespace, func_name)

        args = [arg for arg in graph.getargs() if arg.concretetype is not ootype.Void]
        if is_method:
            args = args[1:]

        arg_types = [self.lltype_to_cts(arg.concretetype) for arg in args]
        arg_list = ', '.join(arg_types)

        return '%s %s(%s)' % (ret_type, func_name, arg_list)

    def op_to_signature(self, op, func_name):
        ret_type, ret_var = self.llvar_to_cts(op.result)
        func_name = self.escape_name(func_name)

        args = [arg for arg in op.args[1:]
                    if arg.concretetype is not ootype.Void]

        arg_types = [self.lltype_to_cts(arg.concretetype) for arg in args]
        arg_list = ', '.join(arg_types)

        return '%s %s(%s)' % (ret_type, func_name, arg_list)


    def method_signature(self, TYPE, name_or_desc):
        # TODO: use callvirt only when strictly necessary
        if isinstance(TYPE, ootype.Instance):
            if isinstance(name_or_desc, ootype._overloaded_meth_desc):
                name = name_or_desc.name
                METH = name_or_desc.TYPE
                virtual = True
            else:
                name = name_or_desc
                owner, meth = TYPE._lookup(name)
                METH = meth._TYPE
                virtual = getattr(meth, '_virtual', True)
            class_name = self.db.class_name(TYPE)
            full_name = 'class %s::%s' % (class_name, name)
            returntype = self.lltype_to_cts(METH.RESULT)
            arg_types = [self.lltype_to_cts(ARG) for ARG in METH.ARGS if ARG is not ootype.Void]
            arg_list = ', '.join(arg_types)
            return '%s %s(%s)' % (returntype, full_name, arg_list), virtual

        elif isinstance(TYPE, (ootype.BuiltinType, ootype.StaticMethod)):
            assert isinstance(name_or_desc, str)
            name = name_or_desc
            if isinstance(TYPE, ootype.StaticMethod):
                METH = TYPE
            else:
                METH = oopspec.get_method(TYPE, name)
            class_name = self.lltype_to_cts(TYPE)
            if isinstance(TYPE, ootype.Dict):
                KEY = TYPE._KEYTYPE
                VALUE = TYPE._VALUETYPE
                name = name_or_desc
                if KEY is ootype.Void and VALUE is ootype.Void and name == 'll_get_items_iterator':
                    # ugly, ugly special case
                    ret_type = 'class ' + PYPY_DICT_ITEMS_ITERATOR % ('int32', 'int32')
                elif VALUE is ootype.Void and METH.RESULT is ootype.Dict.VALUETYPE_T:
                    ret_type = 'void'
                else:
                    ret_type = self.lltype_to_cts(METH.RESULT)
                    ret_type = dict_of_void_ll_copy_hack(TYPE, ret_type)
            else:
                ret_type = self.lltype_to_cts(METH.RESULT)
            generic_types = getattr(TYPE, '_generic_types', {})
            arg_types = [self.lltype_to_cts(arg) for arg in METH.ARGS if
                         arg is not ootype.Void and \
                         generic_types.get(arg, arg) is not ootype.Void]
            arg_list = ', '.join(arg_types)
            return '%s %s::%s(%s)' % (ret_type, class_name, name, arg_list), False

        else:
            assert False

def dict_of_void_ll_copy_hack(TYPE, ret_type):
    # XXX: ugly hack to make the ll_copy signature correct when
    # CustomDict is special-cased to DictOfVoid.
    if isinstance(TYPE, ootype.CustomDict) and TYPE._VALUETYPE is ootype.Void:
        return ret_type.replace('Dict`2', 'DictOfVoid`2')
    else:
        return ret_type
