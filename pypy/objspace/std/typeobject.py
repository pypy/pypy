from pypy.objspace.std.objspace import *
from pypy.interpreter.function import Function, StaticMethod
from pypy.interpreter.argument import Arguments
from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import std_dict_descr, issubtypedef, Member
from pypy.objspace.std.objecttype import object_typedef

from copy_reg import _HEAPTYPE

class W_TypeObject(W_Object):
    from pypy.objspace.std.typetype import type_typedef as typedef

    lazyloaders = {} # can be overridden by specific instances

    def __init__(w_self, space, name, bases_w, dict_w,
                 overridetypedef=None):
        W_Object.__init__(w_self, space)
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w
        w_self.ensure_static__new__()
        w_self.nslots = 0
        w_self.w_bestbase = None

        # initialize __module__ in the dict
        if '__module__' not in dict_w:
            try:
                caller = space.getexecutioncontext().framestack.top()
            except IndexError:
                w_globals = w_locals = space.newdict([])
            else:
                w_globals = caller.w_globals
                w_str_name = space.wrap('__name__')
                try:
                    w_name = space.getitem(w_globals, w_str_name)
                except OperationError:
                    pass
                else:
                    dict_w['__module__'] = w_name

        if overridetypedef is not None:
            w_self.instancetypedef = overridetypedef
            w_self.hasdict = overridetypedef.hasdict
            w_self.__flags__ = 0 # not a heaptype
            if overridetypedef.base is not None:
                w_self.w_bestbase = space.gettypeobject(overridetypedef.base)
        else:
            w_self.__flags__ = _HEAPTYPE
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
            hasoldstylebase = False
            w_most_derived_base_with_slots = None
            for w_base in bases_w:
                if not isinstance(w_base, W_TypeObject):
                    hasoldstylebase = True
                    continue
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
            if w_most_derived_base_with_slots:
                nslots = w_most_derived_base_with_slots.nslots
                w_self.w_bestbase = w_most_derived_base_with_slots
            else:
                nslots = 0

            if w_self.w_bestbase is None:
                w_self.w_bestbase = bases_w[0]

            wantdict = True
            if '__slots__' in dict_w:
                wantdict = False

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
                                                 space.wrap("__dict__ slot disallowed: we already got one"))
                        wantdict = True
                    else:
                        # create member
                        w_self.dict_w[slot_name] = space.wrap(Member(nslots, slot_name, w_self))
                        nslots += 1

            w_self.nslots = nslots
                        
            wantdict = wantdict or hasoldstylebase

            if wantdict and not w_self.hasdict:
                w_self.dict_w['__dict__'] = space.wrap(std_dict_descr)
                w_self.hasdict = True
               
            w_type = space.type(w_self)
            if not space.is_true(space.is_(w_type, space.w_type)):
                mro_func = w_type.lookup('mro')
                mro_func_args = Arguments(space, [w_self])
                w_mro = space.call_args(mro_func, mro_func_args)
                w_self.mro_w = space.unpackiterable(w_mro)
                return

        w_self.mro_w = w_self.compute_mro()

    def compute_mro(w_self):
        return compute_C3_mro(w_self.space, w_self)

    def ensure_static__new__(w_self):
        # special-case __new__, as in CPython:
        # if it is a Function, turn it into a static method
        if '__new__' in w_self.dict_w:
            w_new = w_self.dict_w['__new__']
            if isinstance(w_new, Function):
                w_self.dict_w['__new__'] = StaticMethod(w_new)

    def getdictvalue(w_self, space, attr):
        try:
            return w_self.dict_w[attr]
        except KeyError:
            if w_self.lazyloaders:
                if attr in w_self.lazyloaders:
                    loader = w_self.lazyloaders[attr]
                    del w_self.lazyloaders[attr]
                    w_value = loader()
                    if w_value is not None:   # None means no such attribute
                        w_self.dict_w[attr] = w_value
                        return w_value
            return None

    def lookup(w_self, key):
        # note that this doesn't call __get__ on the result at all
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = space.getdictvalue(w_class, key)
            if w_value is not None:
                return w_value
        return None

    def lookup_where(w_self, key):
        # like lookup() but also returns the parent class in which the
        # attribute was found
        space = w_self.space
        for w_class in w_self.mro_w:
            w_value = space.getdictvalue(w_class, key)
            if w_value is not None:
                return w_class, w_value
        return None, None

    def check_user_subclass(w_self, w_subtype):
        space = w_self.space
        if not isinstance(w_subtype, W_TypeObject):
            raise OperationError(space.w_TypeError,
                space.wrap("X is not a type object (%s)" % (
                    space.type(w_subtype).name)))
        if not space.is_true(space.issubtype(w_subtype, w_self)):
            raise OperationError(space.w_TypeError,
                space.wrap("%s.__new__(%s): %s is not a subtype of %s" % (
                    w_self.name, w_subtype.name, w_subtype.name, w_self.name)))
        if w_self.instancetypedef is not w_subtype.instancetypedef:
            raise OperationError(space.w_TypeError,
                space.wrap("%s.__new__(%s) is not safe, use %s.__new__()" % (
                    w_self.name, w_subtype.name, w_subtype.name)))
        return w_subtype

    def getdict(w_self):
        # XXX should return a <dictproxy object>
        if w_self.lazyloaders:
            for attr in w_self.lazyloaders.keys():
                w_self.getdictvalue(w_self.space, attr)
            del w_self.lazyloaders
        space = w_self.space
        dictspec = []
        for key, w_value in w_self.dict_w.items():
            dictspec.append((space.wrap(key), w_value))
        return space.newdict(dictspec)

    def setdict(w_self, w_dict):
        space = w_self.space
        raise OperationError(space.w_TypeError,
                             space.wrap("attribute '__dict__' of type objects "
                                        "is not writable"))

    def unwrap(w_self):
        if hasattr(w_self.instancetypedef, 'fakedcpytype'):
            return w_self.instancetypedef.fakedcpytype
        from pypy.objspace.std.model import UnwrapError
        raise UnwrapError(w_self)

    def is_heaptype(w_self):
        return w_self.__flags__&_HEAPTYPE

    def get_module(w_self):
        space = w_self.space
        if '__module__' in w_self.dict_w:
            return w_self.dict_w['__module__']
        else:
            return space.wrap('__builtin__')
        

def call__Type(space, w_type, __args__):
    # special case for type(x)
    if space.is_true(space.is_(w_type, space.w_type)):
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
        space.get_and_call_args(w_descr, w_newobject, __args__)
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
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.set(w_descr,w_type,space.type(w_type))
    w_type.dict_w[name] = w_value

def delattr__Type_ANY(space, w_type, w_name):
    if w_type.lazyloaders:
        w_type.getdict()    # force un-lazification
    name = space.str_w(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            space.delete(w_descr, space.type(w_type))
    del w_type.dict_w[name]
    
# XXX __delattr__
# XXX __hash__ ??

# ____________________________________________________________


abstract_mro = gateway.applevel("""
    def abstract_mro(klass):
        # abstract/classic mro
        mro = [klass]
        for klass in mro:
            if not isinstance(klass.__bases__, tuple):
                raise TypeError, '__bases__ must be a tuple'
            for base in klass.__bases__:
                if base not in mro:
                    mro.append(base)
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

def _getname(space, w_cls):
    return space.str_w(space.getattr(w_cls, space.wrap('__name__')))

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
