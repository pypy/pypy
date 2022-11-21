# overrides for annotation specific to PyPy codebase
from rpython.annotator.policy import AnnotatorPolicy
from rpython.flowspace.model import Constant
from rpython.annotator.classdesc import InstanceSource

def set_attribute(classdesc, value, attr="_static_lookup_cache"):
    cls = classdesc.pyobj
    if attr in cls.__dict__:
        return
    classdesc.classdict[attr] = Constant(value)
    classdesc.immutable_fields.add(attr)
    classdesc.classdef.add_source_for_attribute(attr, classdesc)
    setattr(cls, attr, value)

class PyPyAnnotatorPolicy(AnnotatorPolicy):
    def __init__(self, space):
        self.lookups = set()
        self.lookups_where = set()
        self.pypytypes = {} # W_Root subclass -> W_TypeObject()
        self.types_w = set()
        self.space = space

    def consider_lookup(self, bookkeeper, attr):
        from pypy.objspace.std import typeobject
        from pypy.interpreter import baseobjspace
        assert attr not in self.lookups
        cached = "cached_%s" % attr
        clsdef = bookkeeper.getuniqueclassdef(StaticLookupCache)
        classdesc = clsdef.classdesc
        set_attribute(classdesc, None, cached)
        for cls, w_type in self.pypytypes.items():
            if cls._static_lookup_cache is not None:
                setattr(cls._static_lookup_cache, cached, w_type._lookup(attr))
                source = InstanceSource(bookkeeper, cls._static_lookup_cache)
                clsdef.add_source_for_attribute(cached, source)
        self.lookups.add(attr)

    def consider_lookup_in_type_where(self, bookkeeper, attr):
        assert attr not in self.lookups_where
        from pypy.objspace.std import typeobject
        cached = "cached_where_%s" % attr
        clsdef = bookkeeper.getuniqueclassdef(typeobject.W_TypeObject)
        classdesc = clsdef.classdesc
        classdesc.immutable_fields.add(cached)
        classdesc.classdict[cached] = Constant((None, None))
        clsdef.add_source_for_attribute(cached, classdesc)
        for w_t in self.types_w:
            if not (w_t.is_heaptype() or w_t.is_cpytype()):
                setattr(w_t, cached, w_t._lookup_where(attr))
                source = InstanceSource(bookkeeper, w_t)
                clsdef.add_source_for_attribute(cached, source)
        self.lookups_where.add(attr)

    def specialize__lookup(self, funcdesc, args_s):
        # approach: add to every subclass of W_Root that does not represent a
        # user-defined class an attribute "_static_lookup_cache" which is an
        # instance of StaticLookupCache. for user-defined subclasses of
        # concrete subclasses of W_Root, _static_lookup_cache is None.
        # then add attributes cached_<special_method_name> to the instances of
        # StaticLookupCache, storing the result of looking up a special method
        # from the type
        s_space, s_obj, s_name = args_s
        if s_name.is_constant():
            attr = s_name.const
            def builder(translator, func):
                #print "LOOKUP", attr
                self.consider_lookup(funcdesc.bookkeeper, attr)
                d = {'__name__': '<ann_override_lookup>'}
                exec CACHED_LOOKUP % {'attr': attr} in d
                return translator.buildflowgraph(d['lookup_'+attr])
            return funcdesc.cachedgraph(attr, builder=builder)
        else:
            return funcdesc.cachedgraph(None) # don't specialize

    def specialize__lookup_in_type_where(self, funcdesc, args_s):
        # lookup_in_type_where works differently, we have a w_type, cache the
        # results on that for non-heaptypes
        s_space, s_type, s_name = args_s
        if s_name.is_constant():
            attr = s_name.const
            def builder(translator, func):
                #print "LOOKUP_IN_TYPE_WHERE", attr
                self.consider_lookup_in_type_where(funcdesc.bookkeeper, attr)
                d = {'__name__': '<ann_override_lookup>'}
                exec CACHED_LOOKUP_IN_TYPE_WHERE % {'attr': attr} in d
                return translator.buildflowgraph(d['lookup_in_type_where_'+attr])
            return funcdesc.cachedgraph(attr, builder=builder)
        else:
            return funcdesc.cachedgraph(None)

    def event(self, bookkeeper, what, x):
        from pypy.objspace.std import typeobject
        from pypy.interpreter import baseobjspace
        if what == "classdef_setup" and issubclass(x.classdesc.pyobj, baseobjspace.W_Root):
            classdesc = x.classdesc
            cls = classdesc.pyobj
            if (getattr(cls, "typedef", None) is None or
                    cls.user_overridden_class):
                set_attribute(classdesc, None)
                return
            w_type = self.space.gettypeobject(cls.typedef)
            if w_type.is_heaptype() or w_type.is_cpytype():
                set_attribute(classdesc, None)
                return
            if '_static_lookup_cache' not in cls.__dict__:
                set_attribute(classdesc, StaticLookupCache())
                assert '_static_lookup_cache' in cls.__dict__
            else:
                assert 0, "should not be possible"
            self.pypytypes[cls] = w_type
            clsdef = bookkeeper.getuniqueclassdef(StaticLookupCache)
            for attr in self.lookups:
                cached = "cached_%s" % attr
                w_value = w_type._lookup(attr)
                setattr(cls._static_lookup_cache, cached, w_value)
                source = InstanceSource(bookkeeper, cls._static_lookup_cache)
                clsdef.add_source_for_attribute(cached, source)
        if isinstance(x, typeobject.W_TypeObject):
            clsdef = bookkeeper.getuniqueclassdef(typeobject.W_TypeObject)
            self.types_w.add(x)
            #print "TYPE", x
            for attr in self.lookups_where:
                if not (x.is_heaptype() or x.is_cpytype()):
                    cached = "cached_where_%s" % attr
                    setattr(x, cached, x._lookup_where(attr))
                    source = InstanceSource(bookkeeper, x)
                    clsdef.add_source_for_attribute(cached, source)
        return

class StaticLookupCache(object):
    pass

CACHED_LOOKUP = """
def lookup_%(attr)s(space, w_obj, name):
    cache = w_obj._static_lookup_cache
    if cache is None:
        w_type = space.type(w_obj)
        return w_type.lookup("%(attr)s")
    return cache.cached_%(attr)s
"""

CACHED_LOOKUP_IN_TYPE_WHERE = """
def lookup_in_type_where_%(attr)s(space, w_type, name):
    if not w_type.is_heaptype() and not w_type.is_cpytype():
        return w_type.cached_where_%(attr)s
    return w_type.lookup_where("%(attr)s")
"""
