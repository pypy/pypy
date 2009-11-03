from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

dict_copy       = SMM('copy',          1,
                      doc='D.copy() -> a shallow copy of D')
dict_items      = SMM('items',         1,
                      doc="D.items() -> list of D's (key, value) pairs, as"
                          ' 2-tuples')
dict_keys       = SMM('keys',          1,
                      doc="D.keys() -> list of D's keys")
dict_values     = SMM('values',        1,
                      doc="D.values() -> list of D's values")
dict_has_key    = SMM('has_key',       2,
                      doc='D.has_key(k) -> True if D has a key k, else False')
dict_clear      = SMM('clear',         1,
                      doc='D.clear() -> None.  Remove all items from D.')
dict_get        = SMM('get',           3, defaults=(None,),
                      doc='D.get(k[,d]) -> D[k] if k in D, else d.  d defaults'
                          ' to None.')
dict_pop        = SMM('pop',           2, w_varargs=True,
                      doc='D.pop(k[,d]) -> v, remove specified key and return'
                          ' the corresponding value\nIf key is not found, d is'
                          ' returned if given, otherwise KeyError is raised')
dict_popitem    = SMM('popitem',       1,
                      doc='D.popitem() -> (k, v), remove and return some (key,'
                          ' value) pair as a\n2-tuple; but raise KeyError if D'
                          ' is empty')
dict_setdefault = SMM('setdefault',    3, defaults=(None,),
                      doc='D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d'
                          ' if k not in D')
dict_update     = SMM('update',        1, general__args__=True,
                      doc='D.update(E, **F) -> None.  Update D from E and F:'
                          ' for k in E: D[k] = E[k]\n(if E has keys else: for'
                          ' (k, v) in E: D[k] = v) then: for k in F: D[k] ='
                          ' F[k]')
dict_iteritems  = SMM('iteritems',     1,
                      doc='D.iteritems() -> an iterator over the (key, value)'
                          ' items of D')
dict_iterkeys   = SMM('iterkeys',      1,
                      doc='D.iterkeys() -> an iterator over the keys of D')
dict_itervalues = SMM('itervalues',    1,
                      doc='D.itervalues() -> an iterator over the values of D')
dict_reversed   = SMM('__reversed__',      1)

def dict_reversed__ANY(space, w_dict):
    raise OperationError(space.w_TypeError, space.wrap('argument to reversed() must be a sequence'))

#dict_fromkeys   = MultiMethod('fromkeys',      2, varargs=True)
# This can return when multimethods have been fixed
#dict_str        = StdObjSpace.str

# default application-level implementations for some operations
# most of these (notably not popitem and update*) are overwritten
# in dictmultiobject
# gateway is imported in the stdtypedef module
app = gateway.applevel('''

    # in the following functions we use dict.__setitem__ instead of
    # d[k]=...  because when a subclass of dict override __setitem__,
    # CPython does not call it when doing builtin operations.  The
    # same for other operations.

    def update1(d, o):
        if hasattr(o, 'keys'):
            for k in o.keys():
                dict.__setitem__(d, k, o[k])
        else:
            for k,v in o:
                dict.__setitem__(d, k, v)

    def update(d, *args, **kwargs):
        len_args = len(args)
        if len_args == 1:
            update1(d, args[0])
        elif len_args > 1:
            raise TypeError("update takes at most 1 (non-keyword) argument")
        if kwargs:
            update1(d, kwargs)

    def popitem(d):
        for k in dict.iterkeys(d):
            break
        else:
            raise KeyError("popitem(): dictionary is empty")
        v = dict.__getitem__(d, k)
        dict.__delitem__(d, k)
        return k, v

    def get(d, k, v=None):
        if k in d:
            return dict.__getitem__(d, k)
        else:
            return v

    def setdefault(d, k, v=None):
        if k in d:
            return dict.__getitem__(d, k)
        else:
            dict.__setitem__(d, k, v)
            return v

    def pop(d, k, defaults):     # XXX defaults is actually *defaults
        if len(defaults) > 1:
            raise TypeError, "pop expected at most 2 arguments, got %d" % (
                1 + len(defaults))
        try:
            v = dict.__getitem__(d, k)
            dict.__delitem__(d, k)
        except KeyError, e:
            if defaults:
                return defaults[0]
            else:
                raise e
        return v

    def iteritems(d):
        return iter(dict.items(d))

    def iterkeys(d):
        return iter(dict.keys(d))

    def itervalues(d):
        return iter(dict.values(d))
''', filename=__file__)
#XXX what about dict.fromkeys()?

dict_update__ANY             = app.interphook("update")
dict_popitem__ANY            = app.interphook("popitem")
dict_get__ANY_ANY_ANY        = app.interphook("get")
dict_setdefault__ANY_ANY_ANY = app.interphook("setdefault")
dict_pop__ANY_ANY            = app.interphook("pop")
dict_iteritems__ANY          = app.interphook("iteritems")
dict_iterkeys__ANY           = app.interphook("iterkeys")
dict_itervalues__ANY         = app.interphook("itervalues")
update1                      = app.interphook("update1")

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_dicttype, __args__):
    from pypy.objspace.std.dictmultiobject import W_DictMultiObject
    w_obj = W_DictMultiObject.allocate_and_init_instance(space, w_dicttype)
    return w_obj

# ____________________________________________________________

dict_typedef = StdTypeDef("dict",
    __doc__ = '''dict() -> new empty dictionary.
dict(mapping) -> new dictionary initialized from a mapping object\'s
    (key, value) pairs.
dict(seq) -> new dictionary initialized as if via:
    d = {}
    for k, v in seq:
        d[k] = v
dict(**kwargs) -> new dictionary initialized with the name=value pairs
    in the keyword argument list.  For example:  dict(one=1, two=2)''',
    __new__ = newmethod(descr__new__,
                        unwrap_spec=[gateway.ObjSpace,gateway.W_Root,gateway.Arguments]),
    __hash__ = no_hash_descr,
    )
dict_typedef.registermethods(globals())

# ____________________________________________________________

def descr_dictiter__reduce__(w_self, space):
    """
    This is a slightly special case of pickling.
    Since iteration over a dict is a bit hairy,
    we do the following:
    - create a clone of the dict iterator
    - run it to the original position
    - collect all remaining elements into a list
    At unpickling time, we just use that list
    and create an iterator on it.
    This is of course not the standard way.

    XXX to do: remove this __reduce__ method and do
    a registration with copy_reg, instead.
    """
    from pypy.interpreter.mixedmodule import MixedModule
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('dictiter_surrogate_new')
    w_typeobj = space.gettypeobject(dictiter_typedef)
    
    from pypy.interpreter.mixedmodule import MixedModule
    raise OperationError(
        space.w_RuntimeError,
        space.wrap("cannot pickle dictiters with multidicts"))
    # XXXXXX get that working again
    
    # we cannot call __init__ since we don't have the original dict
    if isinstance(w_self, W_DictIter_Keys):
        w_clone = space.allocate_instance(W_DictIter_Keys, w_typeobj)
    elif isinstance(w_self, W_DictIter_Values):
        w_clone = space.allocate_instance(W_DictIter_Values, w_typeobj)
    elif isinstance(w_self, W_DictIter_Items):
        w_clone = space.allocate_instance(W_DictIter_Items, w_typeobj)
    else:
        msg = "unsupported dictiter type '%s' during pickling" % (w_self, )
        raise OperationError(space.w_TypeError, space.wrap(msg))
    w_clone.space = space
    w_clone.content = w_self.content
    w_clone.len = w_self.len
    w_clone.pos = 0
    w_clone.setup_iterator()
    # spool until we have the same pos
    while w_clone.pos < w_self.pos:
        w_obj = w_clone.next_entry()
        w_clone.pos += 1
    stuff = [w_clone.next_entry() for i in range(w_clone.pos, w_clone.len)]
    w_res = space.newlist(stuff)
    tup      = [
        w_res
    ]
    w_ret = space.newtuple([new_inst, space.newtuple(tup)])
    return w_ret    

# ____________________________________________________________


dictiter_typedef = StdTypeDef("dictionaryiterator",
    __reduce__ = gateway.interp2app(descr_dictiter__reduce__,
                           unwrap_spec=[gateway.W_Root, gateway.ObjSpace]),
    )
