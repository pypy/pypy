from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, overload, Meth, StaticMethod
from pypy.annotation import model as annmodel
from pypy.rpython.rmodel import Repr
from pypy.translator.cli.support import PythonNet

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


## OOType model

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


class NativeInstance(ootype.Instance):
    def __init__(self, assembly, namespace, name, superclass,
                 fields={}, methods={}, _is_root=False, _hints = {}):
        fullname = '%s%s.%s' % (assembly, namespace, name)
        self._namespace = namespace
        self._classname = name
        ootype.Instance.__init__(self, fullname, superclass, fields, methods, _is_root, _hints)


## RPython interface definition

class CliClass(object):
    def __init__(self, INSTANCE, static_methods):
        self._name = INSTANCE._name
        self._INSTANCE = INSTANCE
        self._static_methods = {}
        self._add_methods(static_methods)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _add_methods(self, methods):
        self._static_methods.update(methods)
        for name, meth in methods.iteritems():
            meth._set_attrs(self, name)

    def _lookup(self, meth_name, ARGS):
        meth = self._static_methods[meth_name]
        return meth._get_desc(ARGS)

    def _ann_static_method(self, meth_name, args_s):
        meth = self._static_methods[meth_name]
        return meth._annotate_overloading(args_s)

    def _load_class(self):
        names = self._INSTANCE._namespace.split('.')
        names.append(self._INSTANCE._classname)
        obj = PythonNet
        for name in names:
            obj = getattr(obj, name)
        self._PythonNet_class = obj

    def __getattr__(self, attr):
        if attr in self._static_methods:
            self._load_class()
            return getattr(self._PythonNet_class, attr)
        else:
            raise AttributeError

    def __call__(self, *args):
        self._load_class()
        return self._PythonNet_class(*args)


class Entry(ExtRegistryEntry):
    _type_ = CliClass

    def compute_annotation(self):
        return SomeCliClass()


class CliNamespace(object):
    def __init__(self, name):
        self._name = name

    def __fullname(self, name):
        if self._name is None:
            return name
        else:
            return '%s.%s' % (self._name, name)

    def __getattr__(self, attr):
        from pypy.translator.cli.query import load_class_or_namespace
        name = self.__fullname(attr)
        load_class_or_namespace(name)
        assert attr in self.__dict__
        return getattr(self, attr)

CLR = CliNamespace(None)
