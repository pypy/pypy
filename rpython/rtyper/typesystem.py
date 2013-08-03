
"""typesystem.py -- Typesystem-specific operations for RTyper."""

from rpython.tool.pairtype import extendabletype

from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.error import TyperError

class TypeSystem(object):
    __metaclass__ = extendabletype

    def derefType(self, T):
        raise NotImplementedError()

    def deref(self, obj):
        """Dereference `obj' to concrete object."""
        raise NotImplementedError()

    def check_null(self, repr, hop):
        """Emit operations to check that `hop's argument is not a null object.
"""
        raise NotImplementedError()

    def null_callable(self, T):
        """null callable object of type T"""
        raise NotImplementedError()

    def getcallabletype(self, ARGS, RESTYPE):
        cls = self.callable_trait[0]
        return cls(ARGS, RESTYPE)

    def getcallable(self, graph, getconcretetype=None):
        """Return callable given a Python function."""
        if getconcretetype is None:
            getconcretetype = self.getconcretetype
        llinputs = [getconcretetype(v) for v in graph.getargs()]
        lloutput = getconcretetype(graph.getreturnvar())

        typ, constr = self.callable_trait

        FT = typ(llinputs, lloutput)
        name = graph.name
        if hasattr(graph, 'func') and callable(graph.func):
            # the Python function object can have _llfnobjattrs_, specifying
            # attributes that are forced upon the functionptr().  The idea
            # for not passing these extra attributes as arguments to
            # getcallable() itself is that multiple calls to getcallable()
            # for the same graph should return equal functionptr() objects.
            if hasattr(graph.func, '_llfnobjattrs_'):
                fnobjattrs = graph.func._llfnobjattrs_.copy()
                # can specify a '_name', but use graph.name by default
                name = fnobjattrs.pop('_name', name)
            else:
                fnobjattrs = {}
            # _callable is normally graph.func, but can be overridden:
            # see fakeimpl in extfunc.py
            _callable = fnobjattrs.pop('_callable', graph.func)
            return constr(FT, name, graph = graph, _callable = _callable,
                          **fnobjattrs)
        else:
            return constr(FT, name, graph = graph)

    def getexternalcallable(self, ll_args, ll_result, name, **kwds):
        typ, constr = self.callable_trait

        FT = typ(ll_args, ll_result)
        return constr(FT, name, **kwds)

    def getconcretetype(self, v):
        """Helper called by getcallable() to get the conrete type of a variable
in a graph."""
        raise NotImplementedError()


class LowLevelTypeSystem(TypeSystem):
    name = "lltypesystem"
    callable_trait = (lltype.FuncType, lltype.functionptr)

    def derefType(self, T):
        assert isinstance(T, lltype.Ptr)
        return T.TO

    def deref(self, obj):
        assert isinstance(lltype.typeOf(obj), lltype.Ptr)
        return obj._obj

    def check_null(self, repr, hop):
        # None is a nullptr, which is false; everything else is true.
        vlist = hop.inputargs(repr)
        return hop.genop('ptr_nonzero', vlist, resulttype=lltype.Bool)

    def getconcretetype(self, v):
        return v.concretetype

    def null_callable(self, T):
        return lltype.nullptr(T.TO)

    def generic_is(self, robj1, robj2, hop):
        roriginal1 = robj1
        roriginal2 = robj2
        if robj1.lowleveltype is lltype.Void:
            robj1 = robj2
        elif robj2.lowleveltype is lltype.Void:
            robj2 = robj1
        if (not isinstance(robj1.lowleveltype, lltype.Ptr) or
            not isinstance(robj2.lowleveltype, lltype.Ptr)):
            raise TyperError('is of instances of the non-pointers: %r, %r' % (
                roriginal1, roriginal2))
        if robj1.lowleveltype != robj2.lowleveltype:
            raise TyperError('is of instances of different pointer types: %r, %r' % (
                roriginal1, roriginal2))

        v_list = hop.inputargs(robj1, robj2)
        return hop.genop('ptr_eq', v_list, resulttype=lltype.Bool)

# All typesystems are singletons
LowLevelTypeSystem.instance = LowLevelTypeSystem()

getfunctionptr = LowLevelTypeSystem.instance.getcallable
