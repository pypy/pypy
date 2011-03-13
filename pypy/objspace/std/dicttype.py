from pypy.interpreter.error import OperationError
from pypy.interpreter.mixedmodule import MixedModule
from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM
from pypy.objspace.std.register_all import register_all

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
dict_pop        = SMM('pop',           2, varargs_w=True,
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
dict_viewkeys   = SMM('viewkeys',      1,
                      doc="D.viewkeys() -> a set-like object providing a view on D's keys")
dict_viewitems  = SMM('viewitems',     1,
                      doc="D.viewitems() -> a set-like object providing a view on D's items")
dict_viewvalues = SMM('viewvalues',    1,
                      doc="D.viewvalues() -> an object providing a view on D's values")
dict_reversed   = SMM('__reversed__',      1)

def dict_reversed__ANY(space, w_dict):
    raise OperationError(space.w_TypeError, space.wrap('argument to reversed() must be a sequence'))

register_all(vars(), globals())

def descr_fromkeys(space, w_type, w_keys, w_fill=None):
    from pypy.objspace.std.dictmultiobject import W_DictMultiObject
    if w_fill is None:
        w_fill = space.w_None
    if space.is_w(w_type, space.w_dict):
        w_dict = W_DictMultiObject.allocate_and_init_instance(space, w_type)
        for w_key in space.listview(w_keys):
            w_dict.setitem(w_key, w_fill)
    else:
        w_dict = space.call_function(w_type)
        for w_key in space.listview(w_keys):
            space.setitem(w_dict, w_key, w_fill)
    return w_dict


app = gateway.applevel('''
    def dictrepr(currently_in_repr, d):
        if len(d) == 0:
            return "{}"
        dict_id = id(d)
        if dict_id in currently_in_repr:
            return '{...}'
        currently_in_repr[dict_id] = 1
        try:
            items = []
            # XXX for now, we cannot use iteritems() at app-level because
            #     we want a reasonable result instead of a RuntimeError
            #     even if the dict is mutated by the repr() in the loop.
            for k, v in dict.items(d):
                items.append(repr(k) + ": " + repr(v))
            return "{" +  ', '.join(items) + "}"
        finally:
            try:
                del currently_in_repr[dict_id]
            except:
                pass
''', filename=__file__)

dictrepr = app.interphook("dictrepr")


def descr_repr(space, w_dict):
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return dictrepr(space, w_currently_in_repr, w_dict)


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
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = None,
    __repr__ = gateway.interp2app(descr_repr),
    fromkeys = gateway.interp2app(descr_fromkeys, as_classmethod=True),
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
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('dictiter_surrogate_new')
    w_typeobj = space.gettypeobject(dictiter_typedef)

    raise OperationError(
        space.w_TypeError,
        space.wrap("can't pickle dictionary-keyiterator objects"))
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
    __reduce__ = gateway.interp2app(descr_dictiter__reduce__),
    )

# ____________________________________________________________
# Dict views

dict_keys_typedef = StdTypeDef(
    "dict_keys",
    )

dict_items_typedef = StdTypeDef(
    "dict_items",
    )

dict_values_typedef = StdTypeDef(
    "dict_values",
    )
