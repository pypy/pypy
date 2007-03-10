from pypy.objspace.std.objspace import *
from pypy.interpreter.function import Function, StaticMethod
from pypy.interpreter.argument import Arguments
from pypy.interpreter import gateway
from pypy.interpreter.typedef import weakref_descr
from pypy.objspace.std.stdtypedef import std_dict_descr, issubtypedef, Member
from pypy.objspace.std.objecttype import object_typedef
from pypy.objspace.std.dictproxyobject import W_DictProxyObject
from pypy.rlib.objectmodel import we_are_translated

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

    def __init__(w_self, space, name, bases_w, dict_w,
                 overridetypedef=None):
        w_self.space = space
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w
        w_self.ensure_static__new__()
        w_self.nslots = 0
        w_self.needsdel = False
        w_self.w_bestbase = None
        w_self.weak_subclasses_w = []

        # make sure there is a __doc__ in dict_w
        if '__doc__' not in dict_w:
            dict_w['__doc__'] = space.w_None

        if overridetypedef is not None:
            w_self.instancetypedef = overridetypedef
            w_self.hasdict = overridetypedef.hasdict
            w_self.weakrefable = overridetypedef.weakrefable
            w_self.__flags__ = 0 # not a heaptype
            if overridetypedef.base is not None:
                w_self.w_bestbase = space.gettypeobject(overridetypedef.base)
        else:
            w_self.__flags__ = _HEAPTYPE
            # initialize __module__ in the dict
            if '__module__' not in dict_w:
                try:
                    caller = space.getexecutioncontext().framestack.top()
                except IndexError:
                    w_globals = w_locals = space.newdict()
                else:
                    w_globals = caller.w_globals
                    w_str_name = space.wrap('__name__')
                    w_name = space.finditem(w_globals, w_str_name)
                    if w_name is not None:
                        dict_w['__module__'] = w_name
            # find the most specific typedef
            instancetypedef = object_typedef
            for w_base in bases_w:
                if not isinstance(w_base, W_TypeObject):
                    continue
                if issubtypedef(w_base.instancetypedef, instancetypedef):
                    if instancetypedef is not w_base.instancetypedef:
                        instancetypedef = w_base.instancetypedef
                        w_self.w_bestbase = w_base
                elif not issubtypedef(instancetypedef, w_base.instancetypedef):
                    raise OperationError(space.w_TypeError,
                                space.wrap("instance layout conflicts in "
                                                    "multiple inheritance"))
            if not instancetypedef.acceptable_as_base_class:
                raise OperationError(space.w_TypeError,
                                     space.wrap("type '%s' is not an "
                                                "acceptable base class" %
                                                instancetypedef.name))
            w_self.instancetypedef = instancetypedef
            w_self.hasdict = False
            w_self.weakrefable = False
            hasoldstylebase = False
            w_most_derived_base_with_slots = None
            w_newstyle = None
            for w_base in bases_w:
                if not isinstance(w_base, W_TypeObject):
                    hasoldstylebase = True
                    continue
                if not w_newstyle:
                    w_newstyle = w_base
                if w_base.nslots != 0:
                    if w_most_derived_base_with_slots is None:
                        w_most_derived_base_with_slots = w_base
                    else:
                        if space.is_true(space.issubtype(w_base, w_most_derived_base_with_slots)):
                            w_most_derived_base_with_slots = w_base
                        elif not space.is_true(space.issubtype(w_most_derived_base_with_slots, w_base)):
                            raise OperationError(space.w_TypeError,
                                                 space.wrap("instance layout conflicts in "
                                                            "multiple inheritance"))
                w_self.hasdict = w_self.hasdict or w_base.hasdict
                w_self.needsdel = w_self.needsdel or w_base.needsdel
                w_self.weakrefable = w_self.weakrefable or w_base.weakrefable
            if not w_newstyle: # only classic bases
                raise OperationError(space.w_TypeError,
                                     space.wrap("a new-style class can't have only classic bases"))

            if w_most_derived_base_with_slots:
                nslots = w_most_derived_base_with_slots.nslots
                w_self.w_bestbase = w_most_derived_base_with_slots
            else:
                nslots = 0

            if w_self.w_bestbase is None:
                w_self.w_bestbase = w_newstyle

            wantdict = True
            wantweakref = True
            if '__slots__' in dict_w:
                wantdict = False
                wantweakref = False

                w_slots = dict_w['__slots__']
                if space.is_true(space.isinstance(w_slots, space.w_str)):
                    if space.int_w(space.len(w_slots)) == 0:
                        raise OperationError(space.w_TypeError,
                                             space.wrap('__slots__ must be identifiers'))
                    slot_names_w = [w_slots]
                else:
                    slot_names_w = space.unpackiterable(w_slots)
                for w_slot_name in slot_names_w:
                    slot_name = space.str_w(w_slot_name)
                    # slot_name should be a valid identifier
                    if len(slot_name) == 0:
                        raise OperationError(space.w_TypeError,
                                             space.wrap('__slots__ must be identifiers'))
                    first_char = slot_name[0]
                    if not first_char.isalpha() and first_char != '_':
                        raise OperationError(space.w_TypeError,
                                             space.wrap('__slots__ must be identifiers'))                        
                    for c in slot_name:
                        if not c.isalnum() and c!= '_':
                            raise OperationError(space.w_TypeError,
                                                 space.wrap('__slots__ must be identifiers'))
                    if slot_name == '__dict__':
                        if wantdict or w_self.hasdict:
                            raise OperationError(space.w_TypeError,
                                                 space.wrap("__dict__ slot disallowed: we already got one"))
                        wantdict = True
                    elif slot_name == '__weakref__':
                        if wantweakref or w_self.weakrefable:
                            raise OperationError(space.w_TypeError,
                                                 space.wrap("__weakref__ slot disallowed: we already got one"))
                                                
                        wantweakref = True
                    else:
                        # create member
                        slot_name = _mangle(slot_name, name)
                        # Force interning of slot names.
                        slot_name = space.str_w(space.new_interned_str(slot_name))
                        w_self.dict_w[slot_name] = space.wrap(Member(nslots, slot_name, w_self))
                        nslots += 1

            w_self.nslots = nslots
                        
            wantdict = wantdict or hasoldstylebase

            if wantdict and not w_self.hasdict:
                w_self.dict_w['__dict__'] = space.wrap(std_dict_descr)
                w_self.hasdict = True
            if '__del__' in dict_w:
                w_self.needsdel = True
            if wantweakref and not w_self.weakrefable:
                w_self.dict_w['__weakref__'] = space.wrap(weakref_descr)
                w_self.weakrefable = True
            w_type = space.type(w_self)
            if not space.is_w(w_type, space.w_type):
                if space.config.objspace.std.withtypeversion:
                    w_self.version_tag = None
                w_self.mro_w = []
                mro_func = space.lookup(w_self, 'mro')
                mro_func_args = Arguments(space, [w_self])
                w_mro = space.call_args(mro_func, mro_func_args)
                w_self.mro_w = space.unpackiterable(w_mro)
                return
        w_self.mro_w = w_self.compute_mro()
        if space.config.objspace.std.withtypeversion:
            if w_self.instancetypedef.hasdict:
                w_self.version_tag = None
            else:
                w_self.version_tag = VersionTag()

    def mutated(w_self):
        space = w_self.space
        assert space.config.objspace.std.withtypeversion
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

    # compute the most parent class with the same layout as us
    def get_layout(w_self):
        w_bestbase = w_self.w_bestbase
        if w_bestbase is None: # object
            return w_self
        if w_self.instancetypedef is not w_bestbase.instancetypedef:
            return w_self
        if w_self.nslots == w_bestbase.nslots:
            return w_bestbase.get_layout()
        return w_self

    # compute a tuple that fully describes the instance layout
    def get_full_instance_layout(w_self):
        w_layout = w_self.get_layout()
        return (w_layout, w_self.hasdict, w_self.needsdel, w_self.weakrefable)

    def compute_mro(w_self):
        return compute_C3_mro(w_self.space, w_self)

    def ensure_static__new__(w_self):
        # special-case __new__, as in CPython:
        # if it is a Function, turn it into a static method
        if '__new__' in w_self.dict_w:
            w_new = w_self.dict_w['__new__']
            if isinstance(w_new, Function):
                w_self.dict_w['__new__'] = StaticMethod(w_new)

    def getdictvalue(w_self, space, w_attr):
        return w_self.getdictvalue_w(space, space.str_w(w_attr))
    
    def getdictvalue_w(w_self, space, attr):
        w_value = w_self.dict_w.get(attr, None)
        if w_self.lazyloaders and w_value is None:
            if attr in w_self.lazyloaders:
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
        ec = space.getexecutioncontext()
        #try:
        #    frame = ec.framestack.top()
        #    position_hash = frame.last_instr ^ id(frame.pycode)
        #except IndexError:
        #    position_hash = 0
        version_tag = w_self.version_tag
        if version_tag is None:
            tup = w_self._lookup_where(name)
            return tup
        MASK = 1 << space.config.objspace.std.methodcachesizeexp - 1
        #method_hash = (id(version_tag) ^ position_hash ^ hash(name)) & MASK
        method_hash = ((id(version_tag) >> 3) ^ hash(name)) & MASK
        cached_version_tag = ec.method_cache_versions[method_hash]
        if cached_version_tag is version_tag:
            cached_name = ec.method_cache_names[method_hash]
            if cached_name is name:
                tup = ec.method_cache_lookup_where[method_hash]
                if space.config.objspace.std.withmethodcachecounter:
                    ec.method_cache_hits[name] = \
                            ec.method_cache_hits.get(name, 0) + 1
#                print "hit", w_self, name
                return tup
        tup = w_self._lookup_where(name)
        ec.method_cache_versions[method_hash] = version_tag
        ec.method_cache_names[method_hash] = name
        ec.method_cache_lookup_where[method_hash] = tup
        if space.config.objspace.std.withmethodcachecounter:
            ec.method_cache_misses[name] = \
                    ec.method_cache_misses.get(name, 0) + 1
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
        newdic = space.newdict()
        newdic.initialize_content(dictspec)
        return W_DictProxyObject(newdic)

    def unwrap(w_self, space):
        if w_self.instancetypedef.fakedcpytype is not None:
            return w_self.instancetypedef.fakedcpytype
        from pypy.objspace.std.model import UnwrapError
        raise UnwrapError(w_self)

    def is_heaptype(w_self):
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
        from pypy.module._weakref.interp__weakref import basic_weakref
        w_newref = basic_weakref(space, w_subclass)
        
        for i in range(len(w_self.weak_subclasses_w)):
            w_ref = w_self.weak_subclasses_w[i]
            ob = space.call_function(w_ref)
            if space.is_w(ob, space.w_None):
                w_self.weak_subclasses_w[i] = w_newref
                return
        else:
            w_self.weak_subclasses_w.append(w_newref)

    def remove_subclass(w_self, w_subclass):
        space = w_self.space

        for i in range(len(w_self.weak_subclasses_w)):
            w_ref = w_self.weak_subclasses_w[i]
            ob = space.call_function(w_ref)
            if space.is_w(ob, w_subclass):
                del w_self.weak_subclasses_w[i]
                return

    def get_subclasses(w_self):
        space = w_self.space
        subclasses_w = []
        for w_ref in w_self.weak_subclasses_w:
            w_ob = space.call_function(w_ref)
            if not space.is_w(w_ob, space.w_None):
                subclasses_w.append(w_ob)
        return subclasses_w


    # for now, weakref support for W_TypeObject is hard to get automatically
    _lifeline_ = None
    def getweakref(self):
        return self._lifeline_
    def setweakref(self, space, weakreflifeline):
        self._lifeline_ = weakreflifeline


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
    w_newobject = space.call_args(w_newfunc, __args__.prepend(w_type))
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
    if space.config.objspace.std.withtypeversion:
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
    w_type.dict_w[name] = w_value

def delattr__Type_ANY(space, w_type, w_name):
    if space.config.objspace.std.withtypeversion:
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
