from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.rpython.objectmodel import r_dict

class DictImplementation(object):
    
##     def getitem(self, w_key):
##         pass
##     def setitem(self,  w_key, w_value):
##         pass
##     def delitem(self, w_key):
##         pass
    
##     def length(self):
##         pass
##     def clear(self, w_dict):
##         pass
##     def has_key(self, w_lookup):
##         pass
##     def get(self, w_lookup, w_default):
##         pass

##     def iteritems(self):
##         pass
##     def iterkeys(self):
##         pass
##     def itervalues(self):
##         pass

    def keys(self):
        return [w_k for w_k in self.iterkeys()]
    def values(self):
        return [w_v for w_v in self.itervalues()]
    def items(self):
        return [(w_key, w_value) or w_key, w_value in self.iteritems()]

## class EmptyDictImplementation(DictImplementation):
##     def getitem(self, w_key, w_value):
##         raise KeyError
##     def setitem(self, w_dict, w_key, w_value):
##         assert False
##     def delitem(self, w_dict, w_key, w_value):
##         raise KeyError
##     def length(self):
##         return 0
##     def clear(self, w_dict):
##         pass
##     def has_key(self, w_lookup):
##         return False

class RDictImplementation(DictImplementation):
    def __init__(self, space):
        self.content = r_dict(space.eq_w, space.hash_w)

    def __repr__(self):
        return "%s<%s>" % (self.__class__.__name__, self.content)
        
    def getitem(self, w_key):
        return self.content[w_key]
    def setitem(self, w_key, w_value):
        self.content[w_key] = w_value
    def delitem(self, w_key):
        del self.content[w_key]
        
    def length(self):
        return len(self.content)
    def clear(self):
        self.content.clear()
    def has_key(self, w_lookup):
        return w_lookup in self.content
    def get(self, w_lookup, w_default):
        return self.content.get(w_lookup, w_default)

    def iteritems(self):
        return self.content.iteritems()
    def iterkeys(self):
        return self.content.iterkeys()
    def itervalues(self):
        return self.content.itervalues()

##     def keys(self):
##         return [w_k for w_k in self.iterkeys()]
##     def values(self):
##         return [w_v for w_v in self.itervalues()]
##     def items(self):
##         return [(w_key, w_value) or w_key, w_value in self.iteritems()]

class W_DictMultiObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space, w_otherdict=None):
        w_self.implementation = RDictImplementation(space)
        if w_otherdict is not None:
            from pypy.objspace.std.dicttype import dict_update__ANY_ANY
            dict_update__ANY_ANY(space, w_self, w_otherdict)

    def initialize_content(w_self, list_pairs_w):
        for w_k, w_v in list_pairs_w:
            w_self.implementation.setitem(w_k, w_v)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.implementation)

    def unwrap(w_dict, space):
        result = {}
        for w_key, w_value in w_dict.implementation.iteritems():
            # generic mixed types unwrap
            result[space.unwrap(w_key)] = space.unwrap(w_value)
        return result

    def len(w_self):
        return w_self.implementation.length()

    def get(w_dict, w_key, w_default):
        return w_dict.implementation.get(w_key, w_default)

    def set_str_keyed_item(w_dict, w_key, w_value):
        w_dict.implementation.setitem(w_key, w_value)

registerimplementation(W_DictMultiObject)


def init__DictMulti(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictMultiObject(space)])            # default argument
    w_dict.implementation.clear()
    try:
        space.getattr(w_src, space.wrap("keys"))
    except OperationError:
        list_of_w_pairs = space.unpackiterable(w_src)
        for w_pair in list_of_w_pairs:
            pair = space.unpackiterable(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            w_dict.implementation.setitem(w_k, w_v)
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import dict_update__ANY_ANY
            dict_update__ANY_ANY(space, w_dict, w_src)
    if space.is_true(w_kwds):
        from pypy.objspace.std.dicttype import dict_update__ANY_ANY
        dict_update__ANY_ANY(space, w_dict, w_kwds)

def getitem__DictMulti_ANY(space, w_dict, w_lookup):
    try:
        return w_dict.implementation.getitem(w_lookup)
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)

def setitem__DictMulti_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.implementation.setitem(w_newkey, w_newvalue)

def delitem__DictMulti_ANY(space, w_dict, w_lookup):
    try:
        w_dict.implementation.delitem(w_lookup)
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__DictMulti(space, w_dict):
    return space.wrap(w_dict.implementation.length())

def contains__DictMulti_ANY(space, w_dict, w_lookup):
    return space.newbool(w_dict.implementation.has_key(w_lookup))

dict_has_key__DictMulti_ANY = contains__DictMulti_ANY

def iter__DictMulti(space, w_dict):
    return W_DictMultiIter_Keys(space, w_dict.implementation)

def eq__DictMulti_DictMulti(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.implementation.length() != w_right.implementation.length():
        return space.w_False
    for w_key, w_val in w_left.implementation.content.iteritems():
        try:
            w_rightval = w_right.implementation.getitem(w_key)
        except KeyError:
            return space.w_False
        if not space.eq_w(w_val, w_rightval):
            return space.w_False
    return space.w_True

def characterize(space, aimpl, bimpl):
    """ (similar to CPython) 
    returns the smallest key in acontent for which b's value is different or absent and this value """
    w_smallest_diff_a_key = None
    w_its_value = None
    for w_key, w_val in aimpl.content.iteritems():
        if w_smallest_diff_a_key is None or space.is_true(space.lt(w_key, w_smallest_diff_a_key)):
            try:
                w_bvalue = bimpl.getitem(w_key)
            except KeyError:
                w_its_value = w_val
                w_smallest_diff_a_key = w_key
            else:
                if not space.eq_w(w_val, w_bvalue):
                    w_its_value = w_val
                    w_smallest_diff_a_key = w_key
    return w_smallest_diff_a_key, w_its_value

def lt__DictMulti_DictMulti(space, w_left, w_right):
    # Different sizes, no problem
    leftimpl = w_left.implementation
    rightimpl = w_right.implementation
    if leftimpl.length() < rightimpl.length():
        return space.w_True
    if leftimpl.length() > rightimpl.length():
        return space.w_False

    # Same size
    w_leftdiff, w_leftval = characterize(space, leftimpl, rightimpl)
    if w_leftdiff is None:
        return space.w_False
    w_rightdiff, w_rightval = characterize(space, rightimpl, leftimpl)
    if w_rightdiff is None:
        # w_leftdiff is not None, w_rightdiff is None
        return space.w_True 
    w_res = space.lt(w_leftdiff, w_rightdiff)
    if (not space.is_true(w_res) and
        space.eq_w(w_leftdiff, w_rightdiff) and 
        w_rightval is not None):
        w_res = space.lt(w_leftval, w_rightval)
    return w_res

def dict_copy__DictMulti(space, w_self):
    return W_DictMultiObject(space, w_self)

def dict_items__DictMulti(space, w_self):
    return space.newlist([space.newtuple([w_k, w_v]) for w_k, w_v in w_self.implementation.iteritems()])

def dict_keys__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.keys())

def dict_values__DictMulti(space, w_self):
    return space.newlist(w_self.implementation.values())

def dict_iteritems__DictMulti(space, w_self):
    return W_DictMultiIter_Items(space, w_self.implementation)

def dict_iterkeys__DictMulti(space, w_self):
    return W_DictMultiIter_Keys(space, w_self.implementation)

def dict_itervalues__DictMulti(space, w_self):
    return W_DictMultiIter_Values(space, w_self.implementation)

def dict_clear__DictMulti(space, w_self):
    w_self.implementation.clear()

def dict_get__DictMulti_ANY_ANY(space, w_dict, w_lookup, w_default):
    return w_dict.implementation.get(w_lookup, w_default)

app = gateway.applevel('''
    def dictrepr(currently_in_repr, d):
        # Now we only handle one implementation of dicts, this one.
        # The fix is to move this to dicttype.py, and do a
        # multimethod lookup mapping str to StdObjSpace.str
        # This cannot happen until multimethods are fixed. See dicttype.py
            dict_id = id(d)
            if dict_id in currently_in_repr:
                return '{...}'
            currently_in_repr[dict_id] = 1
            try:
                items = []
                # XXX for now, we cannot use iteritems() at app-level because
                #     we want a reasonable result instead of a RuntimeError
                #     even if the dict is mutated by the repr() in the loop.
                for k, v in d.items():
                    items.append(repr(k) + ": " + repr(v))
                return "{" +  ', '.join(items) + "}"
            finally:
                try:
                    del currently_in_repr[dict_id]
                except:
                    pass
''', filename=__file__)

dictrepr = app.interphook("dictrepr")

def repr__DictMulti(space, w_dict):
    if w_dict.implementation.length() == 0:
        return space.wrap('{}')
    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________
# Iteration

class W_DictMultiIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, implementation):
        w_self.space = space
        w_self.implementation = implementation
        w_self.len = implementation.length()
        w_self.pos = 0
        w_self.setup_iterator()

    def return_entry(w_self, w_key, w_value):
        raise NotImplementedError

registerimplementation(W_DictMultiIterObject)

class W_DictMultiIter_Keys(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.iterkeys()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key in w_self.iterator:
            return w_key
        else:
            return None

class W_DictMultiIter_Values(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.itervalues()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_value in w_self.iterator:
            return w_value
        else:
            return None

class W_DictMultiIter_Items(W_DictMultiIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.implementation.iteritems()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key, w_value in w_self.iterator:
            return w_self.space.newtuple([w_key, w_value])
        else:
            return None


def iter__DictMultiIterObject(space, w_dictiter):
    return w_dictiter

def next__DictMultiIterObject(space, w_dictiter):
    implementation = w_dictiter.implementation
    if implementation is not None:
        if w_dictiter.len != implementation.length():
            w_dictiter.len = -1   # Make this error state sticky
            raise OperationError(space.w_RuntimeError,
                     space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        w_result = w_dictiter.next_entry()
        if w_result is not None:
            w_dictiter.pos += 1
            return w_result
        # no more entries
        w_dictiter.implementation = None
    raise OperationError(space.w_StopIteration, space.w_None)

def len__DictMultiIterObject(space, w_dictiter):
    implementation = w_dictiter.implementation
    if implementation is None or w_dictiter.len == -1:
        return space.wrap(0)
    return space.wrap(w_dictiter.len - w_dictiter.pos)

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
