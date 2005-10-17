
"""typesystem.py -- Typesystem-specific operations for RTyper."""

from pypy.annotation.pairtype import extendabletype

from pypy.rpython.ootypesystem import ootype
from pypy.rpython.lltypesystem import lltype

class TypeSystem(object):
    __metaclass__ = extendabletype

    def __getattr__(self, name):
        """Lazy import to avoid circular dependencies."""
        def load(modname):
            try:
                return __import__("pypy.rpython.%s.%s" % (self.name, modname),
                                  None, None, ['__doc__'])
            except ImportError:
                return None
        if name in ('rclass', 'rpbc', 'rbuiltin'):
            mod = load(name)
            if mod is not None:
                setattr(self, name, mod)
                return mod

        raise AttributeError(name)

    def deref(self, obj):
        """Dereference `obj' to concrete object."""
        raise NotImplementedError()

    def check_null(self, repr, hop):
        """Emit operations to check that `hop's argument is not a null object.
"""
        raise NotImplementedError()

    def getcallable(self, translator, graphfunc, getconcretetype=None):
        """Return callable given a Python function."""
        if getconcretetype is None:
            getconcretetype = self.getconcretetype
        graph = translator.getflowgraph(graphfunc)
        llinputs = [getconcretetype(v) for v in graph.getargs()]
        lloutput = getconcretetype(graph.getreturnvar())

        typ, constr = self.callable_trait
        
        FT = typ(llinputs, lloutput)
        _callable = getattr(graphfunc, '_specializedversionof_', graphfunc)
        return constr(FT, graphfunc.func_name, graph = graph, _callable = _callable)

    def getconcretetype(self, v):
        """Helper called by getcallable() to get the conrete type of a variable
in a graph."""
        raise NotImplementedError()

class LowLevelTypeSystem(TypeSystem):
    name = "lltypesystem"
    callable_trait = (lltype.FuncType, lltype.functionptr)

    def deref(self, obj):
        assert isinstance(lltype.typeOf(obj), lltype.Ptr)
        return obj._obj

    def check_null(self, repr, hop):
        # None is a nullptr, which is false; everything else is true.
        vlist = hop.inputargs(repr)
        return hop.genop('ptr_nonzero', vlist, resulttype=lltype.Bool)

    def getconcretetype(self, v):
        return getattr(v, 'concretetype', lltype.Ptr(lltype.PyObject))

    def isCompatibleType(self, t1, t2):
        return lltype.isCompatibleType(t1, t2)

class ObjectOrientedTypeSystem(TypeSystem):
    name = "ootypesystem"
    callable_trait = (ootype.StaticMethod, ootype.static_meth)

    def deref(self, obj):
        assert isinstance(ootype.typeOf(obj), ootype.OOType)
        return obj

    def isCompatibleType(self, t1, t2):
        return ootype.isCompatibleType(t1, t2)

# All typesystems are singletons
LowLevelTypeSystem.instance = LowLevelTypeSystem()
ObjectOrientedTypeSystem.instance = ObjectOrientedTypeSystem()

# Multiple dispatch on type system and high-level annotation

from pypy.annotation.pairtype import pairtype
from pypy.annotation.model import SomeObject

class __extend__(pairtype(TypeSystem, SomeObject)):
    def rtyper_makerepr((ts, s_obj), rtyper):
        return s_obj.rtyper_makerepr(rtyper)

    def rtyper_makekey((ts, s_obj), rtyper):
        if hasattr(s_obj, "rtyper_makekey_ex"):
            return s_obj.rtyper_makekey_ex(rtyper)
        return s_obj.rtyper_makekey()
