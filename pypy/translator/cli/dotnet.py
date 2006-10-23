from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, overload, Meth, StaticMethod
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

    def simple_call(self, *args_s):
        return self.cli_class._ann_static_method(self.meth_name, args_s)

    def rtyper_makerepr(self, rtyper):
        return CliStaticMethodRepr(self.cli_class, self.meth_name)

    def rtyper_makekey(self):
        return self.__class__, self.cli_class, self.meth_name



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

    def _build_desc(self, args_v):
        ARGS = tuple([v.concretetype for v in args_v])
        return self.cli_class._lookup(self.meth_name, ARGS)

    def rtype_simple_call(self, hop):
        vlist = []
        for i, repr in enumerate(hop.args_r[1:]):
            vlist.append(hop.inputarg(repr, i+1))
        resulttype = hop.r_result.lowleveltype
        desc = self._build_desc(vlist)
        cDesc = hop.inputconst(ootype.Void, desc)
        return hop.genop("direct_call", [cDesc] + vlist, resulttype=resulttype)



## RPython interface definition


class _static_meth(object):
    def __init__(self, TYPE):
        self._TYPE = TYPE

    def _set_attrs(self, cls, name):
        self._cls = cls
        self._name = name

    def _get_desc(self, ARGS):
        assert ARGS == self._TYPE.ARGS
        return self


class _overloaded_static_meth(ootype._overloaded_mixin):
    def __init__(self, *overloadings):
        self._overloadings = overloadings
        self._check_overloadings()

    def _set_attrs(self, cls, name):
        for meth in self._overloadings:
            meth._set_attrs(cls, name)

    def _get_desc(self, ARGS):
        meth = self._resolve_overloading(ARGS)
        assert isinstance(meth, _static_meth)
        return meth._get_desc(ARGS)


class CliClass(object):
    def __init__(self, INSTANCE, static_methods):
        self._name = INSTANCE._name
        self._INSTANCE = INSTANCE
        self._static_methods = static_methods
        for name, meth in static_methods.iteritems():
            meth._set_attrs(self, name)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _lookup(self, meth_name, ARGS):
        meth = self._static_methods[meth_name]
        return meth._get_desc(ARGS)

    def _ann_static_method(self, meth_name, args_s):
        ARGS = tuple([annmodel.annotation_to_lltype(arg_s) for arg_s in args_s])
        desc = self._lookup(meth_name, ARGS)
        RESULT = desc._TYPE.RESULT        
        return annmodel.lltype_to_annotation(RESULT)


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


OBJECT = NativeInstance('[mscorlib]', 'System', 'Object', ootype.ROOT, {},
                        {'ToString': ootype.meth(ootype.Meth([], ootype.String)),
                         })
Object = CliClass(OBJECT, {})

STRING_BUILDER = NativeInstance('[mscorlib]', 'System.Text', 'StringBuilder', OBJECT, {}, {})
STRING_BUILDER._add_methods({'Append': meth(Meth([ootype.String], STRING_BUILDER)),
                             'AppendLine': overload(meth(Meth([ootype.String], STRING_BUILDER)),
                                                    meth(Meth([], STRING_BUILDER)))
                             })
StringBuilder = CliClass(STRING_BUILDER, {})

##CONSOLE = NativeInstance('[mscorlib]', 'System', 'Console', ootype.ROOT, {}, {})
##Console = CliClass(CONSOLE, {'WriteLine': {(ootype.String,): ootype.Void,
##                                           (ootype.Signed,): ootype.Void}})

MATH = NativeInstance('[mscorlib]', 'System', 'Math', OBJECT, {}, {})
Math = CliClass(MATH,
                {'Abs': _overloaded_static_meth(_static_meth(StaticMethod([ootype.Signed], ootype.Signed)),
                                                _static_meth(StaticMethod([ootype.Float], ootype.Float)))
                 })



ARRAY_LIST = NativeInstance('[mscorlib]', 'System.Collections', 'ArrayList', OBJECT, {},
                            {'Add': meth(Meth([OBJECT], ootype.Signed)),
                             'get_Count': meth(Meth([], ootype.Signed))})
ArrayList = CliClass(ARRAY_LIST, {})
