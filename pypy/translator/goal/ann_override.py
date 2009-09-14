# overrides for annotation specific to PyPy codebase
from pypy.annotation.policy import AnnotatorPolicy, Sig
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import specialize
from pypy.interpreter import baseobjspace

def isidentifier(s):
    if not s: return False
    s = s.replace('_', 'x')
    return s[0].isalpha() and s.isalnum()

# patch - mostly for debugging, to enforce some signatures
baseobjspace.ObjSpace.newbool.im_func._annenforceargs_ = Sig(lambda s1,s2: s1,
                                                             bool)


class PyPyAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False

    def __init__(pol, single_space=None):
        pol.lookups = {}
        pol.lookups_where = {}
        pol.pypytypes = {}
        pol.single_space = single_space

    #def override__wrap_exception_cls(pol, space, x):
    #    import pypy.objspace.std.typeobject as typeobject
    #    clsdef = getbookkeeper().getuniqueclassdef(typeobject.W_TypeObject)
    #    return annmodel.SomeInstance(clsdef, can_be_None=True)
    #
    #def override__fake_object(pol, space, x):
    #    from pypy.interpreter import typedef
    #    clsdef = getbookkeeper().getuniqueclassdef(typedef.W_Root)
    #    return annmodel.SomeInstance(clsdef)    
    #
    #def override__cpy_compile(pol, self, source, filename, mode, flags):
    #    from pypy.interpreter import pycode
    #    clsdef = getbookkeeper().getuniqueclassdef(pycode.PyCode)
    #    return annmodel.SomeInstance(clsdef)    

    def specialize__wrap(pol,  funcdesc, args_s):
        from pypy.interpreter.baseobjspace import Wrappable
        from pypy.annotation.classdef import ClassDef
        Wrappable_def = funcdesc.bookkeeper.getuniqueclassdef(Wrappable)
        typ = args_s[1].knowntype
        if isinstance(typ, ClassDef):
            assert typ.issubclass(Wrappable_def)
            typ = Wrappable
        else:
            assert not issubclass(typ, Wrappable)
            assert typ != tuple, "space.wrap(tuple) forbidden; use newtuple()"
            assert typ != list, "space.wrap(list) forbidden; use newlist()"
            assert typ != dict, "space.wrap(dict) forbidden; use newdict()"
            assert typ != object, "degenerated space.wrap(object)"
            if args_s[0].is_constant() and args_s[1].is_constant():
                if typ in (str, bool, int, float):
                    space = args_s[0].const
                    x = args_s[1].const
                    def fold():
                        if typ is str and isidentifier(x):
                            return space.new_interned_str(x)
                        else:
                            return space.wrap(x)
                    builder = specialize.make_constgraphbuilder(2, factory=fold,
                                                                srcmodule='<ann_override.wrap>')
                    return funcdesc.cachedgraph((typ, x), builder=builder)
        return funcdesc.cachedgraph(typ)

    def _remember_immutable(pol, t, cached):
        # for jit benefit
        if cached not in t._immutable_fields_: # accessed this way just
                                               # for convenience
            t._immutable_fields_.append(cached)        
    
    def attach_lookup(pol, t, attr):
        cached = "cached_%s" % attr
        if not t.is_heaptype():
            pol._remember_immutable(t, cached)
            setattr(t, cached, t._lookup(attr))
            return True
        return False

    def attach_lookup_in_type_where(pol, t, attr):
        cached = "cached_where_%s" % attr
        if not t.is_heaptype():
            pol._remember_immutable(t, cached)
            setattr(t, cached, t._lookup_where(attr))
            return True
        return False

    def consider_lookup(pol, bookkeeper, attr):
        from pypy.annotation.classdef import InstanceSource
        assert attr not in pol.lookups
        from pypy.objspace.std import typeobject
        cached = "cached_%s" % attr
        clsdef = bookkeeper.getuniqueclassdef(typeobject.W_TypeObject)
        classdesc = clsdef.classdesc
        classdesc.classdict[cached] = Constant(None)
        clsdef.add_source_for_attribute(cached, classdesc)
        for t in pol.pypytypes:
            if pol.attach_lookup(t, attr):
                source = InstanceSource(bookkeeper, t)
                clsdef.add_source_for_attribute(cached, source)
        pol.lookups[attr] = True

    def consider_lookup_in_type_where(pol, bookkeeper, attr):
        from pypy.annotation.classdef import InstanceSource
        assert attr not in pol.lookups_where
        from pypy.objspace.std import typeobject
        cached = "cached_where_%s" % attr
        clsdef = bookkeeper.getuniqueclassdef(typeobject.W_TypeObject)
        classdesc = clsdef.classdesc
        classdesc.classdict[cached] = Constant((None, None))
        clsdef.add_source_for_attribute(cached, classdesc)
        for t in pol.pypytypes:
            if pol.attach_lookup_in_type_where(t, attr):
                source = InstanceSource(bookkeeper, t)
                clsdef.add_source_for_attribute(cached, source)
        pol.lookups_where[attr] = True

    def specialize__lookup(pol, funcdesc, args_s):
        s_space, s_obj, s_name = args_s
        if s_name.is_constant():
            attr = s_name.const
            def builder(translator, func):
                #print "LOOKUP", attr
                pol.consider_lookup(funcdesc.bookkeeper, attr)
                d = {'__name__': '<ann_override_lookup>'}
                exec CACHED_LOOKUP % {'attr': attr} in d
                return translator.buildflowgraph(d['lookup_'+attr])
            return funcdesc.cachedgraph(attr, builder=builder)
        else:
            pol.lookups[None] = True
            return funcdesc.cachedgraph(None) # don't specialize

    def specialize__lookup_in_type_where(pol, funcdesc, args_s):
        s_space, s_obj, s_name = args_s
        if s_name.is_constant():
            attr = s_name.const
            def builder(translator, func):
                #print "LOOKUP_IN_TYPE_WHERE", attr
                pol.consider_lookup_in_type_where(funcdesc.bookkeeper, attr)
                d = {'__name__': '<ann_override_lookup>'}
                exec CACHED_LOOKUP_IN_TYPE_WHERE % {'attr': attr} in d
                return translator.buildflowgraph(d['lookup_in_type_where_'+attr])
            return funcdesc.cachedgraph(attr, builder=builder)
        else:
            pol.lookups_where[None] = True
            return funcdesc.cachedgraph(None)

    def event(pol, bookkeeper, what, x):
        from pypy.objspace.std import typeobject
        if isinstance(x, typeobject.W_TypeObject):
            from pypy.annotation.classdef import InstanceSource
            clsdef = bookkeeper.getuniqueclassdef(typeobject.W_TypeObject)
            pol.pypytypes[x] = True
            #print "TYPE", x
            for attr in pol.lookups:
                if attr and pol.attach_lookup(x, attr):
                    cached = "cached_%s" % attr
                    source = InstanceSource(bookkeeper, x)
                    clsdef.add_source_for_attribute(cached, source)
            for attr in pol.lookups_where:
                if attr and pol.attach_lookup_in_type_where(x, attr):
                    cached = "cached_where_%s" % attr
                    source = InstanceSource(bookkeeper, x)
                    clsdef.add_source_for_attribute(cached, source)
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
