from pypy.objspace.std.objspace import *
from pypy.interpreter.function import Function, StaticMethod
from pypy.interpreter.typedef import attrproperty_w
from pypy.objspace.std.stdtypedef import issubtypedef

class W_TypeObject(W_Object):
    from pypy.objspace.std.typetype import type_typedef as typedef

    def __init__(w_self, space, name, bases_w, dict_w, overridetypedef=None):
        W_Object.__init__(w_self, space)
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w
        w_self.ensure_static__new__()
        w_self.mro_w = compute_C3_mro(w_self)   # XXX call type(w_self).mro()
        if overridetypedef is not None:
            w_self.instancetypedef = overridetypedef
        else:
##            # find the most specific typedef
##            longest_mro = [space.object_typedef]
##            for w_base in bases_w:
##                mro = w_base.instancetypedef.mro(space)
##                if len(mro) > len(longest_mro):
##                    longest_mro = mro
##            # check that it is a sub-typedef of all other ones
##            for w_base in bases_w:
##                if w_base.instancetypedef not in longest_mro:
##                    raise OperationError(space.w_TypeError,
##                                space.wrap("instance layout conflicts in "
##                                                    "multiple inheritance"))
##            w_self.instancetypedef = longest_mro[0]
            
            assert bases_w  # typetype.descr__new__ should take care that there
                            # is always at least one base
            instancetypedef = bases_w[0].instancetypedef
            w_self.instancetypedef = instancetypedef
            # check that the remaining bases don't have an incompatible 'layout'
            for w_base in bases_w[1:]:
                if not issubtypedef(instancetypedef, w_base.instancetypedef):
                    raise OperationError(space.w_TypeError,
                                space.wrap("instance layout conflicts in "
                                                    "multiple inheritance"))

    def ensure_static__new__(w_self):
        # special-case __new__, as in CPython:
        # if it is a Function, turn it into a static method
        if '__new__' in w_self.dict_w:
            w_new = w_self.dict_w['__new__']
            if isinstance(w_new, Function):
                w_self.dict_w['__new__'] = StaticMethod(w_new)

    def lookup(w_self, key):
        # note that this doesn't call __get__ on the result at all
        # XXX this should probably also return the (parent) class in which
        # the attribute was found
        space = w_self.space
        for w_class in w_self.mro_w:
            try:
                return w_class.dict_w[key]
            except KeyError:
                pass
        return None

    def check_user_subclass(w_self, w_subtype):
        space = w_self.space
        if not space.is_true(space.isinstance(w_subtype, space.w_type)):
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

    hasdict = True
    def getdict(w_self):
        # XXX should return a <dictproxy object>
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


def call__Type(space, w_type, w_args, w_kwds):
    args_w = space.unpacktuple(w_args)
    # special case for type(x)
    if (space.is_true(space.is_(w_type, space.w_type)) and
        len(args_w) == 1 and not space.is_true(w_kwds)):
        return space.type(args_w[0])
    # invoke the __new__ of the type
    w_descr = space.getattr(w_type, space.wrap('__new__'))
    w_extendedargs = space.newtuple([w_type] + args_w)
    w_newobject = space.call(w_descr, w_extendedargs, w_kwds)
    # maybe invoke the __init__ of the type
    if space.is_true(space.isinstance(w_newobject, w_type)):
        w_descr = space.lookup(w_newobject, '__init__')
        if w_descr is not None:
            space.get_and_call(w_descr, w_newobject, w_args, w_kwds)
    return w_newobject

def issubtype__Type_Type(space, w_type1, w_type2):
    return space.newbool(w_type2 in w_type1.mro_w)

def repr__Type(space, w_obj):
    return space.wrap("<pypy type '%s'>" % w_obj.name)  # XXX remove 'pypy'

def getattr__Type_ANY(space, w_type, w_name):
    name = space.unwrap(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            return space.get(w_descr,w_type,space.type(w_type))
    w_value = w_type.lookup(name)
    if w_value is not None:
        # __get__(None, type): turns e.g. functions into unbound methods
        return space.get(w_value, space.w_None, w_type)
    if w_descr is not None:
        return space.get(w_descr,w_type,space.type(w_type))
    raise OperationError(space.w_AttributeError,w_name)

def setattr__Type_ANY_ANY(space, w_type, w_name, w_value):
    name = space.unwrap(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            return space.set(w_descr,w_type,space.type(w_type))
    w_type.dict_w[name] = w_value
    
# XXX __delattr__
# XXX __hash__ ??

# ____________________________________________________________

def compute_C3_mro(cls):
    order = []
    orderlists = [list(base.mro_w) for base in cls.bases_w]
    orderlists.append([cls] + cls.bases_w)
    while orderlists:
        for candidatelist in orderlists:
            candidate = candidatelist[0]
            if mro_blockinglist(candidate, orderlists) is None:
                break    # good candidate
        else:
            mro_error(orderlists)  # no candidate found
        assert candidate not in order
        order.append(candidate)
        for i in range(len(orderlists)-1, -1, -1):
            if orderlists[i][0] == candidate:
                del orderlists[i][0]
                if len(orderlists[i]) == 0:
                    del orderlists[i]
    return order

def mro_blockinglist(candidate, orderlists):
    for lst in orderlists:
        if candidate in lst[1:]:
            return lst
    return None  # good candidate

def mro_error(orderlists):
    cycle = []
    candidate = orderlists[-1][0]
    space = candidate.space
    if candidate in orderlists[-1][1:]:
        # explicit error message for this specific case
        raise OperationError(space.w_TypeError,
            space.wrap("duplicate base class " + candidate.name))
    while candidate not in cycle:
        cycle.append(candidate)
        nextblockinglist = mro_blockinglist(candidate, orderlists)
        candidate = nextblockinglist[0]
    del cycle[:cycle.index(candidate)]
    cycle.append(candidate)
    cycle.reverse()
    names = [cls.name for cls in cycle]
    raise OperationError(space.w_TypeError,
        space.wrap("cycle among base classes: " + ' < '.join(names)))

# ____________________________________________________________

register_all(vars())
