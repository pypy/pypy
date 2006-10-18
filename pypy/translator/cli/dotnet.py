from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem import ootype
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr

## Annotation model

class SomeCliClass(annmodel.SomeObject):
    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        return SomeCliStaticMethod(self.const, s_attr.const)

    def simple_call(self, *s_args):
        assert self.is_constant()
        return annmodel.SomeOOInstance(self.const._INSTANCE)

    def rtyper_makerepr(self, rtyper):
        return CliClassRepr(self.const)

    def rtyper_makekey(self):
        return self.__class__, self.const


class SomeCliStaticMethod(annmodel.SomeObject):
    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def rtyper_makerepr(self, rtyper):
        return CliStaticMethodRepr(self.cli_class, self.meth_name)

    def rtyper_makekey(self):
        return self.__class__, self.cli_class, self.meth_name

    def simple_call(self, *args_s):
        return self.cli_class._ann_static_method(self.meth_name, args_s)



## Rtyper model

class CliClassRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class):
        self.cli_class = cli_class

    def rtype_getattr(self, hop):
        return hop.inputconst(ootype.Void, self.cli_class)

    def rtype_simple_call(self, hop):
        # TODO: resolve constructor overloading
        INSTANCE = hop.args_r[0].cli_class._INSTANCE
        cINST = hop.inputconst(ootype.Void, INSTANCE)
        vlist = hop.inputargs(*hop.args_r)[1:] # discard the first argument
        return hop.genop("new", [cINST]+vlist, resulttype=hop.r_result.lowleveltype)

class CliStaticMethodRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def _build_desc(self, args_v, resulttype):
        argtypes = [v.concretetype for v in args_v]
        return StaticMethodDesc(self.cli_class._INSTANCE._name, self.meth_name, argtypes, resulttype)

    def rtype_simple_call(self, hop):
        vlist = []
        for i, repr in enumerate(hop.args_r[1:]):
            vlist.append(hop.inputarg(repr, i+1))
        resulttype = hop.r_result.lowleveltype
        desc = self._build_desc(vlist, resulttype)
        v_desc = hop.inputconst(ootype.Void, desc)
        return hop.genop("direct_call", [v_desc] + vlist, resulttype=resulttype)



## RPython interface definition

class StaticMethodDesc(object):
    def __init__(self, class_name, method_name, argtypes, resulttype):
        # TODO: maybe use ootype.StaticMeth for describing signature?
        self.class_name = class_name
        self.method_name = method_name
        self.argtypes = argtypes
        self.resulttype = resulttype


class CliClass(object):
    def __init__(self, INSTANCE, static_methods):
        self._INSTANCE = INSTANCE
        self._static_methods = static_methods

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _lookup(self, meth_name, args_s):
        # TODO: handle conversion
        overloads = self._static_methods[meth_name]
        argtypes = tuple([annmodel.annotation_to_lltype(arg_s) for arg_s in args_s])
        return argtypes, overloads[argtypes]

    def _ann_static_method(self, meth_name, args_s):
        argtypes, rettype = self._lookup(meth_name, args_s)
        return annmodel.lltype_to_annotation(rettype)


class Entry(ExtRegistryEntry):
    _type_ = CliClass

    def compute_annotation(self):
        return SomeCliClass()


## OOType model

class NativeInstance(ootype.Instance):
    def __init__(self, assembly, namespace, name, superclass,
                 fields={}, methods={}, _is_root=False, _hints = {}):
        fullname = '%s%s.%s' % (assembly, namespace, name)
        ootype.Instance.__init__(self, fullname, superclass, fields, methods, _is_root, _hints)

STRING_BUILDER = NativeInstance('[mscorlib]', 'System.Text', 'StringBuilder', ootype.ROOT, {}, {})
STRING_BUILDER._add_methods({'Append': ootype.meth(ootype.Meth([ootype.String], STRING_BUILDER))})
StringBuilder = CliClass(STRING_BUILDER, {})

CONSOLE = NativeInstance('[mscorlib]', 'System', 'Console', ootype.ROOT, {}, {})
Console = CliClass(CONSOLE, {'WriteLine': {(ootype.String,): ootype.Void,
                                          (ootype.Signed,): ootype.Void}})
MATH = NativeInstance('[mscorlib]', 'System', 'Math', ootype.ROOT, {}, {})
Math = CliClass(MATH, {'Abs': {(ootype.Signed,): ootype.Signed,
                               (ootype.Float,): ootype.Float}})

ARRAY_LIST = NativeInstance('[mscorlib]', 'System.Collections', 'ArrayList', ootype.ROOT, {},
                            {'Add': ootype.meth(ootype.Meth([ootype.ROOT], ootype.Signed)),
                             'get_Count': ootype.meth(ootype.Meth([], ootype.Signed))})
ArrayList = CliClass(ARRAY_LIST, {})
