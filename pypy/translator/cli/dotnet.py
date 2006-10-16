from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem import ootype
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr

class SomeCliClass(annmodel.SomeObject):
    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        return SomeCliStaticMethod(self.const, s_attr.const)

    def rtyper_makerepr(self, rtyper):
        return CliClassRepr(self.const)

    def rtyper_makekey(self):
        return self.__class__, self.const

class SomeCliStaticMethod(annmodel.SomeObject):
    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def simple_call(self, *args_s):
        return self.cli_class.annotate_method(self.meth_name, args_s)

    def rtyper_makerepr(self, rtyper):
        return CliStaticMethodRepr(self.cli_class, self.meth_name)

    def rtyper_makekey(self):
        return self.__class__, self.cli_class, self.meth_name


class CliClassRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class):
        self.cli_class = cli_class

    def rtype_getattr(self, hop):
        return hop.inputconst(ootype.Void, self.cli_class)

class StaticMethodDesc(object):
    def __init__(self, class_name, method_name, argtypes, resulttype):
        # TODO: maybe use ootype.StaticMeth for describing signature?
        self.class_name = class_name
        self.method_name = method_name
        self.argtypes = argtypes
        self.resulttype = resulttype


class CliStaticMethodRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def _build_desc(self, args_v, resulttype):
        argtypes = [v.concretetype for v in args_v]
        return StaticMethodDesc(self.cli_class.name, self.meth_name, argtypes, resulttype)

    def rtype_simple_call(self, hop):
        vlist = []
        for i, repr in enumerate(hop.args_r[1:]):
            vlist.append(hop.inputarg(repr, i+1))
        resulttype = hop.r_result.lowleveltype
        desc = self._build_desc(vlist, resulttype)
        v_desc = hop.inputconst(ootype.Void, desc)
        return hop.genop("direct_call", [v_desc] + vlist, resulttype=resulttype)


class CliClass(object):
    def __init__(self, name, methods):
        self.name = name
        self.methods = methods

    def annotate_method(self, meth_name, args_s):
        argtypes, rettype = self._lookup(meth_name, args_s)
        return annmodel.lltype_to_annotation(rettype)

    def _lookup(self, meth_name, args_s):
        # TODO: handle conversion
        overloads = self.methods[meth_name]
        argtypes = tuple([_annotation_to_lltype(arg_s) for arg_s in args_s])
        return argtypes, overloads[argtypes]

def _annotation_to_lltype(arg_s):
    if isinstance(arg_s, annmodel.SomeString):
        return ootype.String
    else:
        return annmodel.annotation_to_lltype(arg_s)

class Entry(ExtRegistryEntry):
    _type_ = CliClass

    def compute_annotation(self):
        return SomeCliClass()

Console = CliClass('System.Console',
                   {'WriteLine': {(ootype.String,): ootype.Void,
                                  (ootype.Signed,): ootype.Void,
                                  (ootype.String, ootype.Signed): ootype.Void }
                    })
Math = CliClass('System.Math',
                {'Abs': {(ootype.Signed,): ootype.Signed}
                 })
