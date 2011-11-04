from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import delegate_String2Unicode
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std import slicetype
from pypy.objspace.std.inttype import wrapint

from pypy.objspace.std.stringtype import wrapstr, wrapchar, sliced, \
     stringendswith, stringstartswith


class W_StringSliceObject(W_Object):
    from pypy.objspace.std.stringtype import str_typedef as typedef

    def __init__(w_self, str, start, stop):
        assert start >= 0
        assert stop >= 0 
        w_self.str = str
        w_self.start = start
        w_self.stop = stop

    def force(w_self):
        if w_self.start == 0 and w_self.stop == len(w_self.str):
            return w_self.str
        str = w_self.str[w_self.start:w_self.stop]
        w_self.str = str
        w_self.start = 0
        w_self.stop = len(str)
        return str

    def str_w(w_self, space):
        return w_self.force()

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r[%d:%d])" % (w_self.__class__.__name__,
                                  w_self.str, w_self.start, w_self.stop)


registerimplementation(W_StringSliceObject)


def delegate_slice2str(space, w_strslice):
    return wrapstr(space, w_strslice.force())

def delegate_slice2unicode(space, w_strslice):
    w_str = wrapstr(space, w_strslice.force())
    return delegate_String2Unicode(space, w_str)

# ____________________________________________________________

def contains__StringSlice_String(space, w_self, w_sub):
    sub = w_sub._value
    return space.newbool(w_self.str.find(sub, w_self.start, w_self.stop) >= 0)


def _convert_idx_params(space, w_self, w_sub, w_start, w_end):
    length = w_self.stop - w_self.start
    sub = w_sub._value
    start, end = slicetype.unwrap_start_stop(
            space, length, w_start, w_end, True)

    assert start >= 0
    assert end >= 0

    return (w_self.str, sub, w_self.start + start, w_self.start + end)


def str_find__StringSlice_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) = _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.find(sub, start, end)
    if res >= 0:
        return space.wrap(res - w_self.start)
    else:
        return space.wrap(res)

def str_partition__StringSlice_String(space, w_self, w_sub):
    self = w_self.str
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.find(sub, w_self.start, w_self.stop)
    if pos == -1:
        return space.newtuple([w_self, space.wrap(''), space.wrap('')])
    else:
        return space.newtuple([sliced(space, self, w_self.start, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), w_self.stop,
                                      w_self)])

def str_rpartition__StringSlice_String(space, w_self, w_sub):
    self = w_self.str
    sub = w_sub._value
    if not sub:
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = self.rfind(sub, w_self.start, w_self.stop)
    if pos == -1:
        return space.newtuple([space.wrap(''), space.wrap(''), w_self])
    else:
        return space.newtuple([sliced(space, self, w_self.start, pos, w_self),
                               w_sub,
                               sliced(space, self, pos+len(sub), w_self.stop,
                                      w_self)])


def str_count__StringSlice_String_ANY_ANY(space, w_self, w_arg, w_start, w_end): 
    (s, arg, start, end) =  _convert_idx_params(
            space, w_self, w_arg, w_start, w_end)
    return wrapint(space, s.count(arg, start, end))

def str_rfind__StringSlice_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.rfind(sub, start, end)
    if res >= 0:
        return space.wrap(res - w_self.start)
    else:
        return space.wrap(res)

def str_index__StringSlice_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.find(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return space.wrap(res - w_self.start)


def str_rindex__StringSlice_String_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = self.rfind(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return space.wrap(res - w_self.start)

def str_endswith__StringSlice_String_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (u_self, suffix, start, end) = _convert_idx_params(space, w_self,
                                                       w_suffix, w_start, w_end)
    return space.newbool(stringendswith(u_self, suffix, start, end))

def str_endswith__StringSlice_Tuple_ANY_ANY(space, w_self, w_suffixes, w_start, w_end):
    (u_self, _, start, end) = _convert_idx_params(space, w_self,
                                                  space.wrap(''), w_start, w_end)
    for w_suffix in space.fixedview(w_suffixes):
        suffix = space.str_w(w_suffix) 
        if stringendswith(u_self, suffix, start, end):
            return space.w_True
    return space.w_False

def str_startswith__StringSlice_String_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    (u_self, prefix, start, end) = _convert_idx_params(space, w_self,
                                                       w_prefix, w_start, w_end)
    return space.newbool(stringstartswith(u_self, prefix, start, end))

def str_startswith__StringSlice_Tuple_ANY_ANY(space, w_self, w_prefixes, w_start, w_end):
    (u_self, _, start, end) = _convert_idx_params(space, w_self, space.wrap(''),
                                                  w_start, w_end)
    for w_prefix in space.fixedview(w_prefixes):
        prefix = space.str_w(w_prefix)
        if stringstartswith(u_self, prefix, start, end):
            return space.w_True
    return space.w_False

def getitem__StringSlice_ANY(space, w_str, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    slen = w_str.stop - w_str.start
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        exc = space.call_function(space.w_IndexError,
                                  space.wrap("string index out of range"))
        raise OperationError(space.w_IndexError, exc)
    return wrapchar(space, w_str.str[w_str.start + ival])

def getitem__StringSlice_Slice(space, w_str, w_slice):
    w = space.wrap
    length = w_str.stop - w_str.start
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_StringObject.EMPTY
    else:
        s = w_str.str
        start = w_str.start + start
        if step == 1:
            stop = w_str.start + stop
            assert start >= 0 and stop >= 0
            return W_StringSliceObject(s, start, stop)
        else:
            str = "".join([s[start + i*step] for i in range(sl)])
    return wrapstr(space, str)

def getslice__StringSlice_ANY_ANY(space, w_str, w_start, w_stop):
    length = w_str.stop - w_str.start
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    sl = stop - start
    if sl == 0:
        return W_StringObject.EMPTY
    else:
        s = w_str.str
        start = w_str.start + start
        stop = w_str.start + stop
        return W_StringSliceObject(s, start, stop)

def len__StringSlice(space, w_str):
    return space.wrap(w_str.stop - w_str.start)


def str__StringSlice(space, w_str):
    if type(w_str) is W_StringSliceObject:
        return w_str
    return W_StringSliceObject(w_str.str, w_str.start, w_str.stop)


from pypy.objspace.std import stringtype
register_all(vars(), stringtype)
