# overrides for annotation specific to PyPy codebase
from pypy.annotation.policy import AnnotatorPolicy
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import specialize

class PyPyAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False

    def __init__(pol, single_space=None):
        pol.lookups = {}
        pol.lookups_where = {}
        pol.pypytypes = {}
        pol.single_space = single_space

    def override__wrap_exception_cls(pol, space, x):
        import pypy.objspace.std.typeobject as typeobject
        clsdef = getbookkeeper().getclassdef(typeobject.W_TypeObject)
        return annmodel.SomeInstance(clsdef, can_be_None=True)

    def override__fake_object(pol, space, x):
        from pypy.interpreter import typedef
        clsdef = getbookkeeper().getclassdef(typedef.W_Root)
        return annmodel.SomeInstance(clsdef)    

    def override__cpy_compile(pol, self, source, filename, mode, flags):
        from pypy.interpreter import pycode
        clsdef = getbookkeeper().getclassdef(pycode.PyCode)
        return annmodel.SomeInstance(clsdef)    

    def specialize__wrap(pol, bookkeeper, mod, spaceop, func, args, mono):
        from pypy.interpreter.baseobjspace import Wrappable
        ignore, args_w = args.flatten()
        typ = args_w[1].knowntype
        if issubclass(typ, Wrappable):
            typ = Wrappable
        return (func, typ), args
    
    def attach_lookup(pol, t, attr):
        cached = "cached_%s" % attr
        if not t.is_heaptype():
            setattr(t, cached, t.lookup(attr))
            return True
        return False

    def attach_lookup_in_type_where(pol, t, attr):
        cached = "cached_where_%s" % attr
        if not t.is_heaptype():
            setattr(t, cached, t.lookup_where(attr))
            return True
        return False

    def consider_lookup(pol, bookkeeper, attr):
        assert attr not in pol.lookups
        from pypy.objspace.std import typeobject
        cached = "cached_%s" % attr
        clsdef = bookkeeper.getclassdef(typeobject.W_TypeObject)
        setattr(clsdef.cls, cached, None)
        clsdef.add_source_for_attribute(cached, clsdef.cls, clsdef)
        for t in pol.pypytypes:
            if pol.attach_lookup(t, attr):
                clsdef.add_source_for_attribute(cached, t)
        src = CACHED_LOOKUP % {'attr': attr}
        print src
        d = {}
        exec src in d
        fn = d["lookup_%s" % attr]
        pol.lookups[attr] = fn


    def consider_lookup_in_type_where(pol, bookkeeper, attr):
        assert attr not in pol.lookups_where
        from pypy.objspace.std import typeobject
        cached = "cached_where_%s" % attr
        clsdef = bookkeeper.getclassdef(typeobject.W_TypeObject)
        setattr(clsdef.cls, cached, (None, None))
        clsdef.add_source_for_attribute(cached, clsdef.cls, clsdef)
        for t in pol.pypytypes:
            if pol.attach_lookup_in_type_where(t, attr):
                clsdef.add_source_for_attribute(cached, t)
        src = CACHED_LOOKUP_IN_TYPE_WHERE % {'attr': attr}
        print src
        d = {}
        exec src in d
        fn = d["lookup_in_type_where_%s" % attr]
        pol.lookups_where[attr] = fn

    def specialize__lookup(pol, bookkeeper, mod, spaceop, func, args, mono):
        (s_space, s_obj, s_name), _ = args.unpack()
        if s_name.is_constant():
            attr = s_name.const
            if attr not in pol.lookups:
                print "LOOKUP", attr
                pol.consider_lookup(bookkeeper, attr)
            return pol.lookups[attr], args
        else:
            pol.lookups[None] = True
        return func, args

    def specialize__lookup_in_type_where(pol, bookkeeper, mod, spaceop, func, args, mono):
        (s_space, s_obj, s_name), _ = args.unpack()
        if s_name.is_constant():
            attr = s_name.const
            if attr not in pol.lookups_where:
                print "LOOKUP_IN_TYPE_WHERE", attr
                pol.consider_lookup_in_type_where(bookkeeper, attr)
            return pol.lookups_where[attr], args  
        else:
            pol.lookups_where[None] = True
        return func, args

    def event(pol, bookkeeper, what, x):
        from pypy.objspace.std import typeobject
        if isinstance(x, typeobject.W_TypeObject):
            pol.pypytypes[x] = True
            print "TYPE", x
            for attr in pol.lookups:
                if attr:
                    pol.attach_lookup(x, attr)
            for attr in pol.lookups_where:
                if attr:
                    pol.attach_lookup_in_type_where(x, attr)
        return

CACHED_LOOKUP = """
def lookup_%(attr)s(space, w_obj, name):
    w_type = space.type(w_obj)
    if not w_type.is_heaptype():
        return w_type.cached_%(attr)s
    return w_type.lookup("%(attr)s")
"""

CACHED_LOOKUP_IN_TYPE_WHERE = """
def lookup_in_type_where_%(attr)s(space, w_type, name):
    if not w_type.is_heaptype():
        return w_type.cached_where_%(attr)s
    return w_type.lookup_where("%(attr)s")
"""
