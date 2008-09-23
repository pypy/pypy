from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.rlib.objectmodel import r_dict


class W_DictObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    _immutable_ = True
    def __init__(w_self, space, w_otherdict=None):
        if w_otherdict is None:
            w_self.content = r_dict(space.eq_w, space.hash_w)
        else:
            w_self.content = w_otherdict.content.copy()

    def initialize_content(w_self, list_pairs_w):
        for w_k, w_v in list_pairs_w:
            w_self.content[w_k] = w_v

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s)" % (w_self.__class__.__name__, w_self.content)

    def unwrap(w_dict, space):
        result = {}
        for w_key, w_value in w_dict.content.items():
            # generic mixed types unwrap
            result[space.unwrap(w_key)] = space.unwrap(w_value)
        return result

    def len(w_self):
        return len(w_self.content)

    def get(w_dict, w_lookup, w_default):
        return w_dict.content.get(w_lookup, w_default)

    def missing_method(w_dict, space, w_key):
        if not space.is_w(space.type(w_dict), space.w_dict):
            w_missing = space.lookup(w_dict, "__missing__")
            if w_missing is None:
                return None
            return space.call_function(w_missing, w_dict, w_key)
        else:
            return None

    def set_str_keyed_item(w_dict, w_key, w_value, shadows_type=True):
        w_dict.content[w_key] = w_value

registerimplementation(W_DictObject)


def init__Dict(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictObject(space)])            # default argument
    # w_dict.content.clear() - disabled only for CPython compatibility
    if space.findattr(w_src, space.wrap("keys")) is None:
        list_of_w_pairs = space.unpackiterable(w_src)
        for w_pair in list_of_w_pairs:
            pair = space.unpackiterable(w_pair)
            if len(pair)!=2:
                raise OperationError(space.w_ValueError,
                             space.wrap("dict() takes a sequence of pairs"))
            w_k, w_v = pair
            w_dict.content[w_k] = w_v
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import update1
            update1(space, w_dict, w_src)
    if space.is_true(w_kwds):
        from pypy.objspace.std.dicttype import update1
        update1(space, w_dict, w_kwds)

def getitem__Dict_ANY(space, w_dict, w_lookup):
    try:
        return w_dict.content[w_lookup]
    except KeyError:
        w_missing_item = w_dict.missing_method(space, w_lookup)
        if w_missing_item is None:
            raise OperationError(space.w_KeyError, w_lookup)
        else:
            return w_missing_item

def setitem__Dict_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.content[w_newkey] = w_newvalue

def delitem__Dict_ANY(space, w_dict, w_lookup):
    try:
        del w_dict.content[w_lookup]
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__Dict(space, w_dict):
    return space.wrap(len(w_dict.content))

def contains__Dict_ANY(space, w_dict, w_lookup):
    return space.newbool(w_lookup in w_dict.content)

dict_has_key__Dict_ANY = contains__Dict_ANY

def iter__Dict(space, w_dict):
    return W_DictIter_Keys(space, w_dict)

def eq__Dict_Dict(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if len(w_left.content) != len(w_right.content):
        return space.w_False
    for w_key, w_val in w_left.content.iteritems():
        try:
            w_rightval = w_right.content[w_key]
        except KeyError:
            return space.w_False
        if not space.eq_w(w_val, w_rightval):
            return space.w_False
    return space.w_True

def characterize(space, acontent, bcontent):
    """ (similar to CPython) 
    returns the smallest key in acontent for which b's value is different or absent and this value """
    w_smallest_diff_a_key = None
    w_its_value = None
    for w_key, w_val in acontent.iteritems():
        if w_smallest_diff_a_key is None or space.is_true(space.lt(w_key, w_smallest_diff_a_key)):
            try:
                w_bvalue = bcontent[w_key]
            except KeyError:
                w_its_value = w_val
                w_smallest_diff_a_key = w_key
            else:
                if not space.eq_w(w_val, w_bvalue):
                    w_its_value = w_val
                    w_smallest_diff_a_key = w_key
    return w_smallest_diff_a_key, w_its_value

def lt__Dict_Dict(space, w_left, w_right):
    # Different sizes, no problem
    leftcontent = w_left.content
    rightcontent = w_right.content
    if len(leftcontent) < len(rightcontent):
        return space.w_True
    if len(leftcontent) > len(rightcontent):
        return space.w_False

    # Same size
    w_leftdiff, w_leftval = characterize(space, leftcontent, rightcontent)
    if w_leftdiff is None:
        return space.w_False
    w_rightdiff, w_rightval = characterize(space, rightcontent, leftcontent)
    if w_rightdiff is None:
        # w_leftdiff is not None, w_rightdiff is None
        return space.w_True 
    w_res = space.lt(w_leftdiff, w_rightdiff)
    if (not space.is_true(w_res) and
        space.eq_w(w_leftdiff, w_rightdiff) and 
        w_rightval is not None):
        w_res = space.lt(w_leftval, w_rightval)
    return w_res

def dict_copy__Dict(space, w_self):
    return W_DictObject(space, w_self)

def dict_items__Dict(space, w_self):
    return space.newlist([ space.newtuple([w_key, w_value])
                           for w_key, w_value in w_self.content.iteritems() ])

def dict_keys__Dict(space, w_self):
    return space.newlist(w_self.content.keys())

def dict_values__Dict(space, w_self):
    return space.newlist(w_self.content.values())

def dict_iteritems__Dict(space, w_self):
    return W_DictIter_Items(space, w_self)

def dict_iterkeys__Dict(space, w_self):
    return W_DictIter_Keys(space, w_self)

def dict_itervalues__Dict(space, w_self):
    return W_DictIter_Values(space, w_self)

def dict_clear__Dict(space, w_self):
    w_self.content.clear()

def dict_get__Dict_ANY_ANY(space, w_dict, w_lookup, w_default):
    return w_dict.content.get(w_lookup, w_default)

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

def repr__Dict(space, w_dict):
    if len(w_dict.content) == 0:
        return space.wrap('{}')
    ec = space.getexecutioncontext()
    w_currently_in_repr = ec._py_repr
    if w_currently_in_repr is None:
        w_currently_in_repr = ec._py_repr = space.newdict()
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________
# Iteration

class W_DictIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, w_dictobject):
        w_self.space = space
        w_self.content = content = w_dictobject.content
        w_self.len = len(content)
        w_self.pos = 0
        w_self.setup_iterator()
    
    def setup_iterator(w_self):
        raise NotImplementedError("abstract base class")

    def next_entry(w_self):
        raise NotImplementedError("abstract base class")

registerimplementation(W_DictIterObject)

class W_DictIter_Keys(W_DictIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content.iterkeys()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key in w_self.iterator:
            return w_key
        else:
            return None

class W_DictIter_Values(W_DictIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content.itervalues()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_value in w_self.iterator:
            return w_value
        else:
            return None

class W_DictIter_Items(W_DictIterObject):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content.iteritems()
    def next_entry(w_self):
        # note that this 'for' loop only runs once, at most
        for w_key, w_value in w_self.iterator:
            return w_self.space.newtuple([w_key, w_value])
        else:
            return None


def iter__DictIterObject(space, w_dictiter):
    return w_dictiter

def next__DictIterObject(space, w_dictiter):
    content = w_dictiter.content
    if content is not None:
        if w_dictiter.len != len(content):
            w_dictiter.len = -1   # Make this error state sticky
            raise OperationError(space.w_RuntimeError,
                     space.wrap("dictionary changed size during iteration"))
        # look for the next entry
        try:
            w_result = w_dictiter.next_entry()
        except RuntimeError:
            # it's very likely the underlying dict changed during iteration
            raise OperationError(space.w_RuntimeError,
                     space.wrap("dictionary changed during iteration"))
        if w_result is not None:
            w_dictiter.pos += 1
            return w_result
        # no more entries
        w_dictiter.content = None
    raise OperationError(space.w_StopIteration, space.w_None)

def len__DictIterObject(space, w_dictiter):
    content = w_dictiter.content
    if content is None or w_dictiter.len == -1:
        return space.wrap(0)
    return space.wrap(w_dictiter.len - w_dictiter.pos)

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
