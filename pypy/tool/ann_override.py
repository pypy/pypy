# overrides for annotation specific to PyPy codebase
from rpython.annotator.policy import AnnotatorPolicy
from rpython.flowspace.model import Constant
from rpython.annotator import specialize



def isidentifier(s):
    if not s:
        return False
    s = s.replace('_', 'x')
    return s[0].isalpha() and s.isalnum()


class PyPyAnnotatorPolicy(AnnotatorPolicy):
    def __init__(pol, single_space=None):
        pol.lookups = {}
        pol.lookups_where = {}
        pol.pypytypes = {}
        pol.single_space = single_space

    def specialize__wrap(pol,  funcdesc, args_s):
        from pypy.interpreter.baseobjspace import W_Root
        from rpython.annotator.classdef import ClassDef
        W_Root_def = funcdesc.bookkeeper.getuniqueclassdef(W_Root)
        typ = args_s[1].knowntype
        if isinstance(typ, ClassDef):
            assert typ.issubclass(W_Root_def)
            typ = W_Root
        else:
            assert not issubclass(typ, W_Root)
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
        if typ is str:
            if args_s[1].can_be_None:
                typ = (None, str)
        return funcdesc.cachedgraph(typ)

    def _remember_immutable(pol, t, cached):
        # for jit benefit
        if cached not in t._immutable_fields_: # accessed this way just
                                               # for convenience
            t._immutable_fields_.append(cached)

    def attach_lookup(pol, t, attr):
        cached = "cached_%s" % attr
        if not t.is_heaptype() and not t.is_cpytype():
            pol._remember_immutable(t, cached)
            setattr(t, cached, t._lookup(attr))
            return True
        return False

    def attach_lookup_in_type_where(pol, t, attr):
        cached = "cached_where_%s" % attr
        if not t.is_heaptype() and not t.is_cpytype():
            pol._remember_immutable(t, cached)
            setattr(t, cached, t._lookup_where(attr))
            return True
        return False

    def consider_lookup(pol, bookkeeper, attr):
        from rpython.annotator.classdef import InstanceSource
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
        from rpython.annotator.classdef import InstanceSource
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
            from rpython.annotator.classdef import InstanceSource
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
    if not w_type.is_heaptype() and not w_type.is_cpytype():
        return w_type.cached_%(attr)s
    return w_type.lookup("%(attr)s")
"""

CACHED_LOOKUP_IN_TYPE_WHERE = """
def lookup_in_type_where_%(attr)s(space, w_type, name):
    if not w_type.is_heaptype() and not w_type.is_cpytype():
        return w_type.cached_where_%(attr)s
    return w_type.lookup_where("%(attr)s")
"""
