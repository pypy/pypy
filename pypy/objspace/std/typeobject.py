from pypy.objspace.std.objspace import *
from pypy.interpreter.function import Function, StaticMethod
from pypy.interpreter import gateway
from pypy.interpreter.typedef import weakref_descr
from pypy.objspace.std.stdtypedef import std_dict_descr, issubtypedef, Member
from pypy.objspace.std.objecttype import object_typedef
from pypy.objspace.std.dictproxyobject import W_DictProxyObject
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.objectmodel import current_object_addr_as_int
from pypy.rlib.jit import hint
from pypy.rlib.rarithmetic import intmask, r_uint

from copy_reg import _HEAPTYPE

# from compiler/misc.py

MANGLE_LEN = 256 # magic constant from compile.c

def _mangle(name, klass):
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        end = len(klass) + MANGLE_LEN-tlen
        if end < 0:
            klass = ''     # annotator hint
        else:
            klass = klass[:end]

    return "_%s%s" % (klass, name)

class VersionTag(object):
    pass

class W_TypeObject(W_Object):
    from pypy.objspace.std.typetype import type_typedef as typedef

    lazyloaders = {} # can be overridden by specific instances
    version_tag = None

    uses_object_getattribute = False
    # ^^^ for config.objspace.std.getattributeshortcut
    # (False is a conservative default, fixed during real usage)

    def __init__(w_self, space, name, bases_w, dict_w,
                 overridetypedef=None):
        w_self.space = space
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w
        w_self.nslots = 0
        w_self.hasdict = False
        w_self.needsdel = False
        w_self.weakrefable = False
        w_self.w_same_layout_as = None
        w_self.weak_subclasses = []
        w_self.__flags__ = 0           # or _HEAPTYPE
        w_self.instancetypedef = overridetypedef

        if overridetypedef is not None:
            setup_builtin_type(w_self)
            custom_metaclass = False
        else:
            setup_user_defined_type(w_self)
            custom_metaclass = not space.is_w(space.type(w_self), space.w_type)

        if space.config.objspace.std.withtypeversion:
            if w_self.instancetypedef.hasdict or custom_metaclass:
                pass
            else:
                w_self.version_tag = VersionTag()

    def mutated(w_self):
        space = w_self.space
        if space.config.objspace.std.getattributeshortcut:
            w_self.uses_object_getattribute = False
            # ^^^ conservative default, fixed during real usage
        if not space.config.objspace.std.withtypeversion:
            return
        # Invariant: version_tag is None if and only if
        # 'w_self.instancetypedef.hasdict' is True, which is the case
        # for a built-in type that provides its instances with their own
        # __dict__.  If 'hasdict' is True for a type T then it is also
        # True for all subtypes of T; so we don't need to look for
        # version_tags to update in the subclasses of a type T whose
        # version_tag is None.
        if w_self.version_tag is not None:
            w_self.version_tag = VersionTag()
            subclasses_w = w_self.get_subclasses()
            for w_subclass in subclasses_w:
                assert isinstance(w_subclass, W_TypeObject)
                w_subclass.mutated()

    def ready(w_self):
        for w_base in w_self.bases_w:
            if not isinstance(w_base, W_TypeObject):
                continue
            w_base.add_subclass(w_self)

    # compute a tuple that fully describes the instance layout
    def get_full_instance_layout(w_self):
        w_layout = w_self.w_same_layout_as or w_self
        return (w_layout, w_self.hasdict, w_self.needsdel, w_self.weakrefable)

    def compute_default_mro(w_self):
        return compute_C3_mro(w_self.space, w_self)

    def getdictvalue(w_self, space, w_attr):
        return w_self.getdictvalue_w(space, space.str_w(w_attr))
    
    def getdictvalue_w(w_self, space, attr):
        w_value = w_self.dict_w.get(attr, None)
        if w_self.lazyloaders and w_value is None:
            if attr in w_self.lazyloaders:
                # very clever next line: it forces the attr string
                # to be interned.
                w_attr = space.new_interned_str(attr)
                loader = w_self.lazyloaders[attr]
                del w_self.lazyloaders[attr]
                w_value = loader()
                if w_value is not None:   # None means no such attribute
                    w_self.dict_w[attr] = w_value
                    return w_value
        return w_value

    def lookup(w_self, name):
        # note that this doesn't call __get__ on the result at all
        space = w_self.space
        if space.config.objspace.std.withmethodcache:
            return w_self.lookup_where_with_method_cache(name)[1]

        return w_self._lookup(name)

    def lookup_where(w_self, name):
        space = w_self.space
        if space.config.objspace.std.withmethodcache:
            return w_self.lookup_where_with_method_cache(name)

        return w_self._lookup_where(name)

    def lookup_starting_at(w_self, w_starttype, name):
        space = w_self.space
        # XXX Optimize this with method cache
        look = False
        for w_class in w_self.mro_w:
            if w_class is w_starttype:
                look = True
            elif look:
                w_value = w_class.getdictvalue_w(space, name)
                if w_value is not None:
                    return w_value
        return None
                

    def _lookup(w_self, key):
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = w_class.getdictvalue_w(space, key)
            if w_value is not None:
                return w_value
        return None

    def _lookup_where(w_self, key):
        # like lookup() but also returns the parent class in which the
        # attribute was found
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = w_class.getdictvalue_w(space, key)
            if w_value is not None:
                return w_class, w_value
        return None, None

    def lookup_where_with_method_cache(w_self, name):
        space = w_self.space
        assert space.config.objspace.std.withmethodcache
        version_tag = w_self.version_tag
        if version_tag is None:
            tup = w_self._lookup_where(name)
            return tup
        SHIFT = r_uint.BITS - space.config.objspace.std.methodcachesizeexp
        version_tag_as_int = current_object_addr_as_int(version_tag)
        # ^^^Note: if the version_tag object is moved by a moving GC, the
        # existing method cache entries won't be found any more; new
        # entries will be created based on the new address.  The
        # assumption is that the version_tag object won't keep moving all
        # the time - so using the fast current_object_addr_as_int() instead
        # of a slower solution like hash() is still a good trade-off.
        method_hash = r_uint(intmask(version_tag_as_int * hash(name))) >> SHIFT
        cached_version_tag = space.method_cache_versions[method_hash]
        if cached_version_tag is version_tag:
            cached_name = space.method_cache_names[method_hash]
            if cached_name is name:
                tup = space.method_cache_lookup_where[method_hash]
                if space.config.objspace.std.withmethodcachecounter:
                    space.method_cache_hits[name] = \
                            space.method_cache_hits.get(name, 0) + 1
#                print "hit", w_self, name
                return tup
        tup = w_self._lookup_where(name)
        space.method_cache_versions[method_hash] = version_tag
        space.method_cache_names[method_hash] = name
        space.method_cache_lookup_where[method_hash] = tup
        if space.config.objspace.std.withmethodcachecounter:
            space.method_cache_misses[name] = \
                    space.method_cache_misses.get(name, 0) + 1
#        print "miss", w_self, name
        return tup

    def check_user_subclass(w_self, w_subtype):
        space = w_self.space
        if not isinstance(w_subtype, W_TypeObject):
            raise OperationError(space.w_TypeError,
                space.wrap("X is not a type object (%s)" % (
                    space.type(w_subtype).getname(space, '?'))))
        if not space.is_true(space.issubtype(w_subtype, w_self)):
            raise OperationError(space.w_TypeError,
                space.wrap("%s.__new__(%s): %s is not a subtype of %s" % (
                    w_self.name, w_subtype.name, w_subtype.name, w_self.name)))
        if w_self.instancetypedef is not w_subtype.instancetypedef:
            raise OperationError(space.w_TypeError,
                space.wrap("%s.__new__(%s) is not safe, use %s.__new__()" % (
                    w_self.name, w_subtype.name, w_subtype.name)))
        return w_subtype

    def _freeze_(w_self):
        "NOT_RPYTHON.  Forces the lazy attributes to be computed."
        if 'lazyloaders' in w_self.__dict__:
            for attr in w_self.lazyloaders.keys():
                w_self.getdictvalue_w(w_self.space, attr)
            del w_self.lazyloaders
        return False

    def getdict(w_self): # returning a dict-proxy!
        if w_self.lazyloaders:
            w_self._freeze_()    # force un-lazification
        space = w_self.space
        dictspec = []
        for key, w_value in w_self.dict_w.items():
            dictspec.append((space.wrap(key), w_value))
        # speed hack: instantiate a dict object cls directly
        # NB: cannot use newdict, because that could return something else
        # than an instance of DictObjectCls
        newdic = space.DictObjectCls(space)
        newdic.initialize_content(dictspec)
        return W_DictProxyObject(newdic)

    def unwrap(w_self, space):
        if w_self.instancetypedef.fakedcpytype is not None:
            return w_self.instancetypedef.fakedcpytype
        from pypy.objspace.std.model import UnwrapError
        raise UnwrapError(w_self)

    def is_heaptype(w_self):
        w_self = hint(w_self, deepfreeze=True)
        return w_self.__flags__&_HEAPTYPE

    def get_module(w_self):
        space = w_self.space
        if w_self.is_heaptype() and '__module__' in w_self.dict_w:
            return w_self.dict_w['__module__']
        else:
            # for non-heap types, CPython checks for a module.name in the
            # type name.  That's a hack, so we're allowed to use a different
            # hack...
            if ('__module__' in w_self.dict_w and
                space.is_true(space.isinstance(w_self.dict_w['__module__'],
                                               space.w_str))):
                return w_self.dict_w['__module__']
            return space.wrap('__builtin__')

    def add_subclass(w_self, w_subclass):
        space = w_self.space
        if not space.config.translation.rweakref:
            return    # no weakref support, don't keep track of subclasses
        import weakref
        assert isinstance(w_subclass, W_TypeObject)
        newref = weakref.ref(w_subclass)
        for i in range(len(w_self.weak_subclasses)):
            ref = w_self.weak_subclasses[i]
            if ref() is None:
                w_self.weak_subclasses[i] = newref
                return
        else:
            w_self.weak_subclasses.append(newref)

    def remove_subclass(w_self, w_subclass):
        space = w_self.space
        if not space.config.translation.rweakref:
            return    # no weakref support, don't keep track of subclasses
        for i in range(len(w_self.weak_subclasses)):
            ref = w_self.weak_subclasses[i]
            if ref() is w_subclass:
                del w_self.weak_subclasses[i]
                return

    def get_subclasses(w_self):
        space = w_self.space
        if not space.config.translation.rweakref:
            msg = ("this feature requires weakrefs, "
                   "which are not available in this build of PyPy")
            raise OperationError(space.w_RuntimeError,
                                 space.wrap(msg))
        subclasses_w = []
        for ref in w_self.weak_subclasses:
            w_ob = ref()
            if w_ob is not None:
                subclasses_w.append(w_ob)
        return subclasses_w


    # for now, weakref support for W_TypeObject is hard to get automatically
    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline

# ____________________________________________________________
# Initialization of type objects

def get_parent_layout(w_type):
    """Compute the most parent class of 'w_type' whose layout
       is the same as 'w_type', or None if all parents of 'w_type'
       have a different layout than 'w_type'.
    """
    w_starttype = w_type
    while len(w_type.bases_w) > 0:
        w_bestbase = find_best_base(w_type.space, w_type.bases_w)
        if w_type.instancetypedef is not w_bestbase.instancetypedef:
            break
        if w_type.nslots != w_bestbase.nslots:
            break
        w_type = w_bestbase
    if w_type is not w_starttype:
        return w_type
    else:
        return None

def issublayout(w_layout1, w_layout2):
    space = w_layout2.space
    while w_layout1 is not w_layout2:
        w_layout1 = find_best_base(space, w_layout1.bases_w)
        if w_layout1 is None:
            return False
        w_layout1 = w_layout1.w_same_layout_as or w_layout1
    return True

def find_best_base(space, bases_w):
    """The best base is one of the bases in the given list: the one
       whose layout a new type should use as a starting point.
    """
    w_bestbase = None
    for w_candidate in bases_w:
        if not isinstance(w_candidate, W_TypeObject):
            continue
        if w_bestbase is None:
            w_bestbase = w_candidate   # for now
            continue
        candtypedef = w_candidate.instancetypedef
        besttypedef = w_bestbase.instancetypedef
        if candtypedef is besttypedef:
            # two candidates with the same typedef are equivalent unless
            # one has extra slots over the other
            if w_candidate.nslots > w_bestbase.nslots:
                w_bestbase = w_candidate
        elif issubtypedef(candtypedef, besttypedef):
            w_bestbase = w_candidate
    return w_bestbase

def check_and_find_best_base(space, bases_w):
    """The best base is one of the bases in the given list: the one
       whose layout a new type should use as a starting point.
       This version checks that bases_w is an acceptable tuple of bases.
    """
    w_bestbase = find_best_base(space, bases_w)
    if w_bestbase is None:
        raise OperationError(space.w_TypeError,
                             space.wrap("a new-style class can't have "
                                        "only classic bases"))
    if not w_bestbase.instancetypedef.acceptable_as_base_class:
        raise OperationError(space.w_TypeError,
                             space.wrap("type '%s' is not an "
                                        "acceptable base class" %
                                        w_bestbase.instancetypedef.name))

    # check that all other bases' layouts are superclasses of the bestbase
    w_bestlayout = w_bestbase.w_same_layout_as or w_bestbase
    for w_base in bases_w:
        if isinstance(w_base, W_TypeObject):
            w_layout = w_base.w_same_layout_as or w_base
            if not issublayout(w_bestlayout, w_layout):
                raise OperationError(space.w_TypeError,
                                     space.wrap("instance layout conflicts in "
                                                "multiple inheritance"))
    return w_bestbase

def copy_flags_from_bases(w_self, w_bestbase):
    hasoldstylebase = False
    for w_base in w_self.bases_w:
        if not isinstance(w_base, W_TypeObject):
            hasoldstylebase = True
            continue
        w_self.hasdict = w_self.hasdict or w_base.hasdict
        w_self.needsdel = w_self.needsdel or w_base.needsdel
        w_self.weakrefable = w_self.weakrefable or w_base.weakrefable
    w_self.nslots = w_bestbase.nslots
    return hasoldstylebase

def create_all_slots(w_self, hasoldstylebase):
    space = w_self.space
    dict_w = w_self.dict_w
    if '__slots__' not in dict_w:
        wantdict = True
        wantweakref = True
    else:
        wantdict = False
        wantweakref = False
        w_slots = dict_w['__slots__']
        if space.is_true(space.isinstance(w_slots, space.w_str)):
            slot_names_w = [w_slots]
        else:
            slot_names_w = space.unpackiterable(w_slots)
        for w_slot_name in slot_names_w:
            slot_name = space.str_w(w_slot_name)
            if slot_name == '__dict__':
                if wantdict or w_self.hasdict:
                    raise OperationError(space.w_TypeError,
                            space.wrap("__dict__ slot disallowed: "
                                       "we already got one"))
                wantdict = True
            elif slot_name == '__weakref__':
                if wantweakref or w_self.weakrefable:
                    raise OperationError(space.w_TypeError,
                            space.wrap("__weakref__ slot disallowed: "
                                       "we already got one"))
                wantweakref = True
            else:
                create_slot(w_self, slot_name)
    wantdict = wantdict or hasoldstylebase
    if wantdict: create_dict_slot(w_self)
    if wantweakref: create_weakref_slot(w_self)
    if '__del__' in dict_w: w_self.needsdel = True

def create_slot(w_self, slot_name):
    space = w_self.space
    if not valid_slot_name(slot_name):
        raise OperationError(space.w_TypeError,
                             space.wrap('__slots__ must be identifiers'))
    # create member
    slot_name = _mangle(slot_name, w_self.name)
    # Force interning of slot names.
    slot_name = space.str_w(space.new_interned_str(slot_name))
    member = Member(w_self.nslots, slot_name, w_self)
    w_self.dict_w[slot_name] = space.wrap(member)
    w_self.nslots += 1

def create_dict_slot(w_self):
    if not w_self.hasdict:
        w_self.dict_w['__dict__'] = w_self.space.wrap(std_dict_descr)
        w_self.hasdict = True

def create_weakref_slot(w_self):
    if not w_self.weakrefable:
        w_self.dict_w['__weakref__'] = w_self.space.wrap(weakref_descr)
        w_self.weakrefable = True

def valid_slot_name(slot_name):
    if len(slot_name) == 0 or slot_name[0].isdigit():
        return False
    for c in slot_name:
        if not c.isalnum() and c != '_':
            return False
    return True

def setup_user_defined_type(w_self):
    if len(w_self.bases_w) == 0:
        w_self.bases_w = [w_self.space.w_object]
    w_bestbase = check_and_find_best_base(w_self.space, w_self.bases_w)
    w_self.instancetypedef = w_bestbase.instancetypedef
    w_self.__flags__ = _HEAPTYPE

    hasoldstylebase = copy_flags_from_bases(w_self, w_bestbase)
    create_all_slots(w_self, hasoldstylebase)

    w_self.w_same_layout_as = get_parent_layout(w_self)
    ensure_common_attributes(w_self)

def setup_builtin_type(w_self):
    w_self.hasdict = w_self.instancetypedef.hasdict
    w_self.weakrefable = w_self.instancetypedef.weakrefable
    ensure_common_attributes(w_self)

def ensure_common_attributes(w_self):
    ensure_static_new(w_self)
    ensure_doc_attr(w_self)
    if w_self.is_heaptype():
        ensure_module_attr(w_self)
    w_self.mro_w = []      # temporarily
    compute_mro(w_self)

def ensure_static_new(w_self):
    # special-case __new__, as in CPython:
    # if it is a Function, turn it into a static method
    if '__new__' in w_self.dict_w:
        w_new = w_self.dict_w['__new__']
        if isinstance(w_new, Function):
            w_self.dict_w['__new__'] = StaticMethod(w_new)

def ensure_doc_attr(w_self):
    # make sure there is a __doc__ in dict_w
    w_self.dict_w.setdefault('__doc__', w_self.space.w_None)

def ensure_module_attr(w_self):
    # initialize __module__ in the dict (user-defined types only)
    if '__module__' not in w_self.dict_w:
        space = w_self.space
        try:
            caller = space.getexecutioncontext().framestack.top()
        except IndexError:
            pass
        else:
            w_globals = caller.w_globals
            w_name = space.finditem(w_globals, space.wrap('__name__'))
            if w_name is not None:
                w_self.dict_w['__module__'] = w_name

def compute_mro(w_self):
    if w_self.is_heaptype():
        space = w_self.space
        w_metaclass = space.type(w_self)
        w_where, w_mro_func = space.lookup_in_type_where(w_metaclass, 'mro')
        assert w_mro_func is not None      # because there is one in 'type'
        if not space.is_w(w_where, space.w_type):
            w_mro_meth = space.get(w_mro_func, w_self)
            w_mro = space.call_function(w_mro_meth)
            w_self.mro_w = space.viewiterable(w_mro)
            # do some checking here
            return    # done
    w_self.mro_w = w_self.compute_default_mro()[:]

# ____________________________________________________________

def call__Type(space, w_type, __args__):
    # special case for type(x)
    if space.is_w(w_type, space.w_type):
        try:
            w_obj, = __args__.fixedunpack(1)
        except ValueError:
            pass
        else:
            return space.type(w_obj)
    # invoke the __new__ of the type
    w_newfunc = space.getattr(w_type, space.wrap('__new__'))
    w_newobject = space.call_obj_args(w_newfunc, w_type, __args__)
    # maybe invoke the __init__ of the type
    if space.is_true(space.isinstance(w_newobject, w_type)):
        w_descr = space.lookup(w_newobject, '__init__')
        w_result = space.get_and_call_args(w_descr, w_newobject, __args__)
##         if not space.is_w(w_result, space.w_None):
##             raise OperationError(space.w_TypeError,
##                                  space.wrap("__init__() should return None"))
    return w_newobject

def issubtype__Type_Type(space, w_type1, w_type2):
    return space.newbool(w_type2 in w_type1.mro_w)

def repr__Type(space, w_obj):
    w_mod = w_obj.get_module()
    if not space.is_true(space.isinstance(w_mod, space.w_str)):
        mod = None
    else:
        mod = space.str_w(w_mod)
    if not w_obj.is_heaptype() or (mod is not None and mod == '__builtin__'):
        kind = 'type'
    else:
        kind = 'class'
    if mod is not None and mod !='__builtin__':
        return space.wrap("<%s '%s.%s'>" % (kind, mod, w_obj.name))
    else:
        return space.wrap("<%s '%s'>" % (kind, w_obj.name))

def getattr__Type_ANY(space, w_type, w_name):
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            return space.get(w_descr,w_type)
    w_value = w_type.lookup(name)
    if w_value is not None:
        # __get__(None, type): turns e.g. functions into unbound methods
        return space.get(w_value, space.w_None, w_type)
    if w_descr is not None:
        return space.get(w_descr,w_type)
    msg = "type object '%s' has no attribute '%s'" %(w_type.name, name)
    raise OperationError(space.w_AttributeError, space.wrap(msg))

def setattr__Type_ANY_ANY(space, w_type, w_name, w_value):
    # Note. This is exactly the same thing as descroperation.descr__setattr__,
    # but it is needed at bootstrap to avoid a call to w_type.getdict() which
    # would un-lazify the whole type.
    w_type.mutated()
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.set(w_descr, w_type, w_value)
            return
    
    if not w_type.is_heaptype():
        msg = "can't set attributes on type object '%s'" %(w_type.name,)
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if name == "__del__" and name not in w_type.dict_w:
        msg = "a __del__ method added to an existing type will not be called"
        space.warn(msg, space.w_RuntimeWarning)
    w_type.dict_w[name] = w_value

def delattr__Type_ANY(space, w_type, w_name):
    w_type.mutated()
    if w_type.lazyloaders:
        w_type._freeze_()    # force un-lazification
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.delete(w_descr, w_type)
            return
    if not w_type.is_heaptype():
        msg = "can't delete attributes on type object '%s'" %(w_type.name,)
        raise OperationError(space.w_TypeError, space.wrap(msg))
    try:
        del w_type.dict_w[name]
        return
    except KeyError:
        raise OperationError(space.w_AttributeError, w_name)


# ____________________________________________________________


abstract_mro = gateway.applevel("""
    def abstract_mro(klass):
        # abstract/classic mro
        mro = []
        stack = [klass]
        while stack:
            klass = stack.pop()
            if klass not in mro:
                mro.append(klass)
                if not isinstance(klass.__bases__, tuple):
                    raise TypeError, '__bases__ must be a tuple'
                stack += klass.__bases__[::-1]
        return mro
""", filename=__file__).interphook("abstract_mro")

def get_mro(space, klass):
    if isinstance(klass, W_TypeObject):
        return list(klass.mro_w)
    else:
        return space.unpackiterable(abstract_mro(space, klass))


def compute_C3_mro(space, cls):
    order = []
    orderlists = [get_mro(space, base) for base in cls.bases_w]
    orderlists.append([cls] + cls.bases_w)
    while orderlists:
        for candidatelist in orderlists:
            candidate = candidatelist[0]
            if mro_blockinglist(candidate, orderlists) is GOODCANDIDATE:
                break    # good candidate
        else:
            return mro_error(space, orderlists)  # no candidate found
        assert candidate not in order
        order.append(candidate)
        for i in range(len(orderlists)-1, -1, -1):
            if orderlists[i][0] == candidate:
                del orderlists[i][0]
                if len(orderlists[i]) == 0:
                    del orderlists[i]
    return order

GOODCANDIDATE = []

def mro_blockinglist(candidate, orderlists):
    for lst in orderlists:
        if candidate in lst[1:]:
            return lst
    return GOODCANDIDATE # good candidate

def mro_error(space, orderlists):
    cycle = []
    candidate = orderlists[-1][0]
    if candidate in orderlists[-1][1:]:
        # explicit error message for this specific case
        raise OperationError(space.w_TypeError,
            space.wrap("duplicate base class " + candidate.getname(space,"?")))
    while candidate not in cycle:
        cycle.append(candidate)
        nextblockinglist = mro_blockinglist(candidate, orderlists)
        candidate = nextblockinglist[0]
    del cycle[:cycle.index(candidate)]
    cycle.append(candidate)
    cycle.reverse()
    names = [cls.getname(space, "?") for cls in cycle]
    raise OperationError(space.w_TypeError,
        space.wrap("cycle among base classes: " + ' < '.join(names)))

# ____________________________________________________________

register_all(vars())
