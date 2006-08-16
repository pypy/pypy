from pypy.objspace.std.objspace import *
from pypy.interpreter import gateway

from pypy.rpython.objectmodel import r_dict

class W_DictStrObject(W_Object):
    from pypy.objspace.std.dicttype import dict_typedef as typedef

    def __init__(w_self, space):
        w_self.space = space
        w_self.content = None
        w_self.content_str = {}

    def initialize_content(w_self, list_pairs_w): # YYY
        for w_k, w_v in list_pairs_w:
            w_self.setitem(w_k, w_v)

    def getitem(w_dict, w_lookup):
        """ Helper function, raises rpython exceptions. """
        space = w_dict.space
        if w_dict.content is None:
            w_lookup_type = space.type(w_lookup)
            if space.is_w(w_lookup_type, space.w_str):
                return w_dict.content_str[space.str_w(w_lookup)]
            else:
                if w_dict.isSaneHash(w_lookup_type):
                    raise KeyError
                w_dict.str2object()
        return w_dict.content[w_lookup]

    def get(w_dict, w_lookup, w_default):
        """ Helper function, raises rpython exceptions. """
        space = w_dict.space
        if w_dict.content is None:
            w_lookup_type = space.type(w_lookup)
            if space.is_w(w_lookup_type, space.w_str):
                return w_dict.content_str.get(space.str_w(w_lookup), w_default)
            else:
                if w_dict.isSaneHash(w_lookup_type):
                    return w_default
                w_dict.str2object()
        return w_dict.content.get(w_lookup, w_default)

    
    def setitem(w_self, w_k, w_v):
        space = w_self.space
        if w_self.content is not None:
            w_self.content[w_k] = w_v
        else:
            if space.is_w(space.type(w_k), space.w_str):
                w_self.content_str[space.str_w(w_k)] = w_v
            else:
                w_self.str2object()
                w_self.content[w_k] = w_v

    set_str_keyed_item = setitem

    def str2object(w_self):
        """ Moves all items in the content_str dict to content. """
        assert w_self.content_str is not None and w_self.content is None
        
        # create a new r_dict
        w_self.content = r_dict(w_self.space.eq_w, w_self.space.hash_w)
        for k, w_v in w_self.content_str.items():
            w_self.content[w_self.space.wrap(k)] = w_v
        w_self.content_str = None

    def isSaneHash(w_self, w_lookup_type):
        """ Handles the case of a non string key lookup.
        Types that have a sane hash/eq function should allow us to return True
        directly to signal that the key is not in the dict in any case.
        XXX The types should provide such a flag. """
    
        space = w_self.space
        # XXX there are much more types
        return space.is_w(w_lookup_type, space.w_NoneType) or space.is_w(w_lookup_type, space.w_int)

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%s,%s)" % (w_self.__class__.__name__, w_self.content, w_self.content_str)

    def unwrap(w_dict, space): # YYY
        result = {}
        if w_dict.content_str is None:
            for w_key, w_value in w_dict.content.items():
                # generic mixed types unwrap
                result[space.unwrap(w_key)] = space.unwrap(w_value)
        else:
            for key, w_value in w_dict.content_str.items():
                # generic mixed types unwrap
                result[key] = space.unwrap(w_value)
        return result
    
    def len(w_dict):
        if w_dict.content is not None:
            return len(w_dict.content)
        return len(w_dict.content_str)

registerimplementation(W_DictStrObject)


def init__DictStr(space, w_dict, __args__):
    w_src, w_kwds = __args__.parse('dict',
                          (['seq_or_map'], None, 'kwargs'), # signature
                          [W_DictStrObject(space)])            # default argument
    #if w_dict.content is None:      -
    #    w_dict.content_str.clear()  - disabled only for CPython compatibility
    #else:                           -
    #    w_dict.content.clear()      -

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
            w_dict.setitem(w_k, w_v)
    else:
        if space.is_true(w_src):
            from pypy.objspace.std.dicttype import dict_update__ANY_ANY
            dict_update__ANY_ANY(space, w_dict, w_src)
    if space.is_true(w_kwds):
        from pypy.objspace.std.dicttype import dict_update__ANY_ANY
        dict_update__ANY_ANY(space, w_dict, w_kwds)

def getitem__DictStr_ANY(space, w_dict, w_lookup):
    try:
        return w_dict.getitem(w_lookup)
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)

def setitem__DictStr_ANY_ANY(space, w_dict, w_newkey, w_newvalue):
    w_dict.setitem(w_newkey, w_newvalue)

def delitem__DictStr_ANY(space, w_dict, w_lookup):
    try:
        if w_dict.content is None:
            if space.is_w(space.type(w_lookup), space.w_str):
                del w_dict.content_str[space.str_w(w_lookup)]
                return
            else:
                w_dict.str2object()
        del w_dict.content[w_lookup]
    except KeyError:
        raise OperationError(space.w_KeyError, w_lookup)
    
def len__DictStr(space, w_dict):
    return space.wrap(w_dict.len())

def contains__DictStr_ANY(space, w_dict, w_lookup):
    if w_dict.content is None:
        w_lookup_type = space.type(w_lookup)
        if not space.is_w(w_lookup_type, space.w_str):
            if w_dict.isSaneHash(w_lookup_type):
                return space.w_False
            #foo("degenerated in contains: " + space.type(w_lookup).getname(space, '?'))
            w_dict.str2object()
        else:
            return space.newbool(space.str_w(w_lookup) in w_dict.content_str)
    return space.newbool(w_lookup in w_dict.content)

dict_has_key__DictStr_ANY = contains__DictStr_ANY

def iter__DictStr(space, w_dict):
    return dict_iterkeys__DictStr(space, w_dict)

def equal_str_str(space, w_left, w_right):
    """ This is not a multimethod. """
    if len(w_left.content_str) != len(w_right.content_str):
        return space.w_False
    
    for key, w_val in w_left.content_str.iteritems():
        try:
            w_rightval = w_right.content_str[key]
        except KeyError:
            return space.w_False
        if not space.eq_w(w_val, w_rightval):
            return space.w_False
    return space.w_True

def equal_object_object(space, w_left, w_right):
    """ This is not a multimethod. """
    
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
    
def eq__DictStr_DictStr(space, w_left, w_right):
    if space.is_w(w_left, w_right):
        return space.w_True

    if w_left.content_str is not None and w_right.content_str is not None:
        return equal_str_str(space, w_left, w_right)

    if w_left.content is None:
        w_left.str2object()
    if w_right.content is None:
        w_right.str2object()

    return equal_object_object(space, w_left, w_right)

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

def lt__DictStr_DictStr(space, w_left, w_right):
    # XXX would it make sense to make str special cases?
    if w_left.content is None:
        w_left.str2object()
    if w_right.content is None:
        w_right.str2object()

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

def dict_copy__DictStr(space, w_self):
    w_new_dict = W_DictStrObject(space)
    if w_self.content is None:
        w_new_dict.content = None
        w_new_dict.content_str = w_self.content_str.copy()
    else:
        w_new_dict.content = w_self.content.copy()
        w_new_dict.content_str = None
    return w_new_dict

def dict_items__DictStr(space, w_self):
    if w_self.content is not None:
        l = [space.newtuple([w_key, w_value]) for w_key, w_value in w_self.content.iteritems()]
    else:
        l = [space.newtuple([space.wrap(key), w_value]) for key, w_value in w_self.content_str.iteritems()]
    return space.newlist(l)

def dict_keys__DictStr(space, w_self):
    if w_self.content is None:
        return space.newlist([space.wrap(x) for x in w_self.content_str.keys()])
    else:
        return space.newlist(w_self.content.keys())

def dict_values__DictStr(space, w_self):
    if w_self.content is None:
        l = w_self.content_str.values()
    else:
        l = w_self.content.values()
    return space.newlist(l)

def dict_iteritems__DictStr(space, w_self):
    if w_self.content is None:
        return W_DictIter_Items_str(space, w_self)
    return W_DictIter_Items_obj(space, w_self)

def dict_iterkeys__DictStr(space, w_self):
    if w_self.content is None:
        return W_DictIter_Keys_str(space, w_self)
    return W_DictIter_Keys_obj(space, w_self)

def dict_itervalues__DictStr(space, w_self):
    if w_self.content is None:
        return W_DictIter_Values_str(space, w_self)
    return W_DictIter_Values_obj(space, w_self)

def dict_clear__DictStr(space, w_self):
    if w_self.content is None:
        w_self.content_str.clear()
    else:
        w_self.content.clear()

def dict_get__DictStr_ANY_ANY(space, w_dict, w_lookup, w_default):
    return w_dict.get(w_lookup, w_default)

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

def repr__DictStr(space, w_dict):
    if w_dict.len() == 0:
        return space.wrap('{}')

    w_currently_in_repr = space.getexecutioncontext()._py_repr
    return dictrepr(space, w_currently_in_repr, w_dict)


# ____________________________________________________________
# Iteration

class W_DictStrIterObject(W_Object):
    from pypy.objspace.std.dicttype import dictiter_typedef as typedef

    def __init__(w_self, space, w_dictobject):
        w_self.space = space
        w_self.w_dictobject = w_dictobject
        w_self.content = w_dictobject.content
        w_self.content_str = w_dictobject.content_str
        w_self.len = w_dictobject.len()
        w_self.pos = 0
        w_self.setup_iterator()

    def handleMutation(w_self):
        space = w_self.space
        w_self.len = -1   # Make this error state sticky
        raise OperationError(space.w_RuntimeError,
                 space.wrap("dictionary changed size during iteration"))

registerimplementation(W_DictStrIterObject)

class W_DictStrIter_Keys(W_DictStrIterObject):
    pass

class W_DictIter_Keys_obj(W_DictStrIter_Keys):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content.iterkeys()

    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for w_key in w_self.iterator:
            return w_key
        else:
            return None

class W_DictIter_Keys_str(W_DictStrIter_Keys):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content_str.iterkeys()

    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for key in w_self.iterator:
            return w_self.space.wrap(key)
        else:
            return None

class W_DictStrIter_Values(W_DictStrIterObject):
    pass

class W_DictIter_Values_obj(W_DictStrIter_Values):
    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for w_value in w_self.iterator:
            return w_value
        else:
            return None

    def setup_iterator(w_self):
        w_self.iterator = w_self.content.itervalues()

class W_DictIter_Values_str(W_DictStrIter_Values):
    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for w_value in w_self.iterator:
            return w_value
        else:
            return None

    def setup_iterator(w_self):
        w_self.iterator = w_self.content_str.itervalues()

class W_DictStrIter_Items(W_DictStrIterObject):
    pass

class W_DictIter_Items_obj(W_DictStrIter_Items):
    def setup_iterator(w_self):
        w_self.iterator = w_self.content.iteritems()
    
    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for w_key, w_value in w_self.iterator:
            return w_self.space.newtuple([w_key, w_value])
        else:
            return None

class W_DictIter_Items_str(W_DictStrIter_Items):
    def setup_iterator(w_self):
        w_self.iterator_str = w_self.content_str.iteritems()

    def next_entry(w_self):
        # note that these 'for' loops only run once, at most

        for key, w_value in w_self.iterator_str:
            return w_self.space.newtuple([w_self.space.wrap(key), w_value])
        else:
            return None

def iter__DictStrIterObject(space, w_dictiter):
    return w_dictiter

def next__DictStrIterObject(space, w_dictiter):
    # iterate over the string dict even if the dictobject's data was forced
    # to degenerate. just bail out if the obj's dictionary size differs.
    if (w_dictiter.content_str is not None and w_dictiter.w_dictobject.content_str is None
        and len(w_dictiter.w_dictobject.content) != w_dictiter.len):
        w_dictiter.handleMutation()

    if w_dictiter.content_str is not None:
        if w_dictiter.len != len(w_dictiter.content_str):
            w_dictiter.handleMutation()
        # look for the next entry
        w_result = w_dictiter.next_entry()
        if w_result is not None:
            w_dictiter.pos += 1
            return w_result
        # no more entries
        w_dictiter.content_str = None
    elif w_dictiter.content is not None:
        if w_dictiter.len != len(w_dictiter.content):
            w_dictiter.handleMutation()
        # look for the next entry
        w_result = w_dictiter.next_entry()
        if w_result is not None:
            w_dictiter.pos += 1
            return w_result
        # no more entries
        w_dictiter.content = None
    raise OperationError(space.w_StopIteration, space.w_None)

def len__DictStrIterObject(space, w_dictiter):
    # doesn't check for mutation?
    if (w_dictiter.content is None and w_dictiter.content_str is None) or w_dictiter.len == -1:
        return space.wrap(0)
        
    return space.wrap(w_dictiter.len - w_dictiter.pos)

# ____________________________________________________________

from pypy.objspace.std import dicttype
register_all(vars(), dicttype)
