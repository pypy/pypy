"""
Translate between PyPy ootypesystem and .NET Common Type System
"""

import exceptions

from py.builtin import set
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.option import getoption
from pypy.translator.cli import oopspec

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

class CliType(object):
    def typename(self):
        raise NotImplementedError

    def __str__(self):
        return self.typename()

    def __hash__(self):
        return hash(self.typename())

    def __eq__(self, other):
        return self.typename() == other.typename()

    def __ne__(self, other):
        return self.typename() != other.typename()


class CliPrimitiveType(CliType):
    def __init__(self, name):
        self.name = name

    def typename(self):
        return self.name


class CliReferenceType(CliType):
    prefix = 'class '
    
    def typename(self):
        return self.prefix + self.classname()

    def classname(self):
        raise NotImplementedError

class CliClassType(CliReferenceType):
    def __init__(self, assembly, name):
        self.assembly = assembly
        self.name = name

    def classname(self):
        if self.assembly:
            return '[%s]%s' % (self.assembly, self.name)
        else:
            return self.name

class CliValueType(CliClassType):
    prefix = 'valuetype '


class CliGenericType(CliReferenceType):
    def __init__(self, assembly, name, numparam):
        self.assembly = assembly
        self.name = name
        self.numparam = numparam

    def classname(self):
        paramtypes = [self.paramtype(i) for i in range(self.numparam)]
        thistype = self.specialize(*paramtypes)
        return thistype.classname()

    def specialize(self, *types):
        assert len(types) == self.numparam
        return CliSpecializedType(self, types)

    def paramtype(self, num):
        assert 0 <= num < self.numparam
        return CliPrimitiveType('!%d' % num)

class CliSpecializedType(CliReferenceType):
    def __init__(self, generic_type, arg_types):
        self.generic_type = generic_type
        self.arg_types = arg_types

    def classname(self):
        assembly = self.generic_type.assembly
        name = self.generic_type.name
        numparam = self.generic_type.numparam
        arglist = ', '.join([arg.typename() for arg in self.arg_types])
        return '[%s]%s`%d<%s>' % (assembly, name, numparam, arglist)

class CliArrayType(CliType):

    def __init__(self, itemtype):
        self.itemtype = itemtype

    def typename(self):
        return '%s[]' % self.itemtype.typename()


T = CliPrimitiveType
class types:
    void =    T('void')
    int32 =   T('int32')
    uint32 =  T('unsigned int32')
    int64 =   T('int64')
    uint64 =  T('unsigned int64')
    bool =    T('bool')
    float64 = T('float64')
    char =    T('char')
    string =  T('string')

    weakref = CliClassType('pypylib', 'pypy.runtime.WeakReference')
    type = CliClassType('mscorlib', 'System.Type')
    object = CliClassType('mscorlib', 'System.Object')
    list = CliGenericType('pypylib', 'pypy.runtime.List', 1)
    list_of_void = CliClassType('pypylib', 'pypy.runtime.ListOfVoid')
    dict = CliGenericType('pypylib', 'pypy.runtime.Dict', 2)
    dict_void_void = CliClassType('pypylib', 'pypy.runtime.DictVoidVoid')
    dict_items_iterator = CliGenericType('pypylib', 'pypy.runtime.DictItemsIterator', 2)
    string_builder = CliClassType('pypylib', 'pypy.runtime.StringBuilder')
del T

WEAKREF = types.weakref.classname()
PYPY_DICT_OF_VOID = '[pypylib]pypy.runtime.DictOfVoid`2<%s, int32>'


_lltype_to_cts = {
    ootype.Void: types.void,
    ootype.Signed: types.int32,    
    ootype.Unsigned: types.uint32,
    ootype.SignedLongLong: types.int64,
    ootype.UnsignedLongLong: types.uint64,
    ootype.Bool: types.bool,
    ootype.Float: types.float64,
    ootype.Char: types.char,
    ootype.UniChar: types.char,
    ootype.Class: types.type,
    ootype.String: types.string,
    ootype.StringBuilder: types.string_builder,
    ootype.Unicode: types.string,
    ootype.UnicodeBuilder: types.string_builder,
    ootype.WeakReference: types.weakref,

    # maps generic types to their ordinal
    ootype.List.SELFTYPE_T: types.list,
    ootype.List.ITEMTYPE_T: types.list.paramtype(0),
    ootype.Dict.SELFTYPE_T: types.dict,
    ootype.Dict.KEYTYPE_T: types.dict.paramtype(0),
    ootype.Dict.VALUETYPE_T: types.dict.paramtype(1),
    ootype.DictItemsIterator.SELFTYPE_T: types.dict_items_iterator,
    ootype.DictItemsIterator.KEYTYPE_T: types.dict_items_iterator.paramtype(0),
    ootype.DictItemsIterator.VALUETYPE_T: types.dict_items_iterator.paramtype(1),
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
    "unaligned", "unbox", "volatile", "xor", "ole"])
    # ole is not a keyword, but mono ilasm fails if you use it as a field/method name

    types = types # for convenience

    def __init__(self, db):
        self.db = db

    def escape_name(self, name):
        """Mangle then name if it's a ilasm reserved word"""
        if name in self.ILASM_KEYWORDS:
            return "'%s'" % name
        else:
            return name

    def lltype_to_cts(self, t):
        if t is ootype.ROOT:
            return types.object
        elif isinstance(t, lltype.Ptr) and isinstance(t.TO, lltype.OpaqueType):
            return types.object
        elif isinstance(t, ootype.Instance):
            if getattr(t, '_is_value_type', False):
                cls = CliValueType
            else:
                cls = CliClassType
            NATIVE_INSTANCE = t._hints.get('NATIVE_INSTANCE', None)
            if NATIVE_INSTANCE:
                return cls(None, NATIVE_INSTANCE._name)
            else:
                name = self.db.pending_class(t)
                return cls(None, name)
        elif isinstance(t, ootype.Record):
            name = self.db.pending_record(t)
            return CliClassType(None, name)
        elif isinstance(t, ootype.StaticMethod):
            delegate = self.db.record_delegate(t)
            return CliClassType(None, delegate)
        elif isinstance(t, ootype.Array):
            item_type = self.lltype_to_cts(t.ITEM)
            if item_type == types.void: # special case: Array of Void
                return types.list_of_void
            return CliArrayType(item_type)
        elif isinstance(t, ootype.List):
            item_type = self.lltype_to_cts(t.ITEM)
            if item_type == types.void: # special case: List of Void
                return types.list_of_void
            return types.list.specialize(item_type)
        elif isinstance(t, ootype.Dict):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            if value_type == types.void: # special cases: Dict with voids
                if key_type == types.void:
                    return types.dict_void_void
                else:
                    # XXX
                    return CliClassType(None, PYPY_DICT_OF_VOID % key_type)
            return types.dict.specialize(key_type, value_type)
        elif isinstance(t, ootype.DictItemsIterator):
            key_type = self.lltype_to_cts(t._KEYTYPE)
            value_type = self.lltype_to_cts(t._VALUETYPE)
            if key_type == types.void:
                key_type = types.int32 # placeholder
            if value_type == types.void:
                value_type = types.int32 # placeholder
            return types.dict_items_iterator.specialize(key_type, value_type)

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

        arg_types = [self.lltype_to_cts(arg.concretetype).typename() for arg in args]
        arg_list = ', '.join(arg_types)

        return '%s %s(%s)' % (ret_type, func_name, arg_list)

    def op_to_signature(self, op, func_name):
        ret_type, ret_var = self.llvar_to_cts(op.result)
        func_name = self.escape_name(func_name)

        args = [arg for arg in op.args[1:]
                    if arg.concretetype is not ootype.Void]

        arg_types = [self.lltype_to_cts(arg.concretetype).typename() for arg in args]
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
            full_name = 'class %s::%s' % (class_name, self.escape_name(name))
            returntype = self.lltype_to_cts(METH.RESULT)
            arg_types = [self.lltype_to_cts(ARG).typename() for ARG in METH.ARGS if ARG is not ootype.Void]
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
                    ret_type = types.dict_items_iterator.specialize(types.int32, types.int32)
                elif VALUE is ootype.Void and METH.RESULT is ootype.Dict.VALUETYPE_T:
                    ret_type = types.void
                else:
                    ret_type = self.lltype_to_cts(METH.RESULT)
                    ret_type = dict_of_void_ll_copy_hack(TYPE, ret_type)
            else:
                ret_type = self.lltype_to_cts(METH.RESULT)
            generic_types = getattr(TYPE, '_generic_types', {})
            arg_types = [self.lltype_to_cts(arg).typename() for arg in METH.ARGS if
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
        return ret_type.typename().replace('Dict`2', 'DictOfVoid`2')
    else:
        return ret_type
