from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import *
from pypy.objspace.std.register_all import register_all
from pypy.interpreter.error import OperationError

dict_copy       = StdObjSpaceMultiMethod('copy',          1)
dict_items      = StdObjSpaceMultiMethod('items',         1)
dict_keys       = StdObjSpaceMultiMethod('keys',          1)
dict_values     = StdObjSpaceMultiMethod('values',        1)
dict_has_key    = StdObjSpaceMultiMethod('has_key',       2)
dict_clear      = StdObjSpaceMultiMethod('clear',         1)
dict_get        = StdObjSpaceMultiMethod('get',           3, defaults=(None,))
dict_pop        = StdObjSpaceMultiMethod('pop',           2, w_varargs=True)
dict_popitem    = StdObjSpaceMultiMethod('popitem',       1)
dict_setdefault = StdObjSpaceMultiMethod('setdefault',    3, defaults=(None,))
dict_update     = StdObjSpaceMultiMethod('update',        2, defaults=((),))
dict_iteritems  = StdObjSpaceMultiMethod('iteritems',     1)
dict_iterkeys   = StdObjSpaceMultiMethod('iterkeys',      1)
dict_itervalues = StdObjSpaceMultiMethod('itervalues',    1)
dict_reversed   = StdObjSpaceMultiMethod('__reversed__',      1)

def dict_reversed__ANY(space, w_dict):
    raise OperationError(space.w_TypeError, space.wrap('argument to reversed() must be a sequence'))

#dict_fromkeys   = MultiMethod('fromkeys',      2, varargs=True)
# This can return when multimethods have been fixed
#dict_str        = StdObjSpace.str

# default application-level implementations for some operations
# gateway is imported in the stdtypedef module
app = gateway.applevel('''

    def update(d, o):
        if hasattr(o, 'keys'):
            for k in o.keys():
                d[k] = o[k]
        else:
            for k,v in o:
                d[k] = v

    def popitem(d):
        k = d.keys()
        if not k:
            raise KeyError("popitem(): dictionary is empty")
        k = k[0]
        v = d[k]
        del d[k]
        return k, v

    def get(d, k, v=None):
        if k in d:
            return d[k]
        else:
            return v

    def setdefault(d, k, v=None):
        if k in d:
            return d[k]
        else:
            d[k] = v
            return v

    def pop(d, k, defaults):     # XXX defaults is actually *defaults
        if len(defaults) > 1:
            raise TypeError, "pop expected at most 2 arguments, got %d" % (
                1 + len(defaults))
        try:
            v = d[k]
            del d[k]
        except KeyError, e:
            if defaults:
                return defaults[0]
            else:
                raise e
        return v

    def iteritems(d):
        return iter(d.items())

    def iterkeys(d):
        return iter(d.keys())

    def itervalues(d):
        return iter(d.values())
''', filename=__file__)
#XXX what about dict.fromkeys()?

dict_update__ANY_ANY         = app.interphook("update")
dict_popitem__ANY            = app.interphook("popitem")
dict_get__ANY_ANY_ANY        = app.interphook("get")
dict_setdefault__ANY_ANY_ANY = app.interphook("setdefault")
dict_pop__ANY_ANY            = app.interphook("pop")
dict_iteritems__ANY          = app.interphook("iteritems")
dict_iterkeys__ANY           = app.interphook("iterkeys")
dict_itervalues__ANY         = app.interphook("itervalues")

register_all(vars(), globals())

# ____________________________________________________________

def descr__new__(space, w_dicttype, __args__):
    from pypy.objspace.std.dictobject import W_DictObject
    w_obj = space.allocate_instance(W_DictObject, w_dicttype)
    W_DictObject.__init__(w_obj, space)
    return w_obj

# ____________________________________________________________

dict_typedef = StdTypeDef("dict",
    __doc__ = '''dict() -> new empty dictionary.
dict(mapping) -> new dictionary initialized from a mapping object's
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
    from pypy.objspace.std.dictobject import \
         W_DictIter_Keys, W_DictIter_Values, W_DictIter_Items
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('dictiter_surrogate_new')
    w_typeobj = space.gettypeobject(dictiter_typedef)
    if isinstance(w_self, W_DictIter_Keys):
        w_clone = space.allocate_instance(W_DictIter_Keys, w_typeobj)
    elif isinstance(w_self, W_DictIter_Values):
        w_clone = space.allocate_instance(W_DictIter_Values, w_typeobj)
    elif isinstance(w_self, W_DictIter_Items):
        w_clone = space.allocate_instance(W_DictIter_Items, w_typeobj)
    # we cannot call __init__ since we don't have the original dict
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
#note: registering in dictobject.py


### fragment for frame object left here
        #w(10),
        #w(self.co_argcount), 
        #w(self.co_nlocals), 
        #w(self.co_stacksize), 
        #w(self.co_flags),
        #w(self.co_code), 
        #space.newtuple(self.co_consts_w), 
        #space.newtuple(self.co_names_w), 
        #space.newtuple([w(v) for v in self.co_varnames]), 
        #w(self.co_filename),
        #w(self.co_name), 
        #w(self.co_firstlineno),
        #w(self.co_lnotab), 
        #space.newtuple([w(v) for v in self.co_freevars]),
        #space.newtuple([w(v) for v in self.co_cellvars]),
        #hidden_applevel=False, magic = 62061 | 0x0a0d0000

