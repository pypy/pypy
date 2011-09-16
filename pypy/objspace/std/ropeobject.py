from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter import gateway
from pypy.rlib.objectmodel import we_are_translated
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.rlib.rarithmetic import ovfcheck
from pypy.objspace.std.stringtype import wrapchar

from pypy.rlib import rope
from pypy.objspace.std.stringobject import (
    mod__String_ANY as mod__Rope_ANY,
    str_format__String as str_format__Rope,
    _upper, _lower, DEFAULT_NOOP_TABLE)

class W_RopeObject(W_Object):
    from pypy.objspace.std.stringtype import str_typedef as typedef
    _immutable_fields_ = ['_node']

    def __init__(w_self, node):
        if not we_are_translated():
            assert node.is_bytestring()
        w_self._node = node

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self._node)

    def unwrap(w_self, space):
        return w_self._node.flatten_string()
    str_w = unwrap

    def create_if_subclassed(w_self):
        if type(w_self) is W_RopeObject:
            return w_self
        return W_RopeObject(w_self._node)

W_RopeObject.EMPTY = W_RopeObject(rope.LiteralStringNode.EMPTY)
W_RopeObject.PREBUILT = [W_RopeObject(rope.LiteralStringNode.PREBUILT[i])
                             for i in range(256)]
del i


def rope_w(space, w_str):
    if isinstance(w_str, W_RopeObject):
        return w_str._node
    return rope.LiteralStringNode(space.str_w(w_str))

registerimplementation(W_RopeObject)

class W_RopeIterObject(W_Object):
    from pypy.objspace.std.itertype import iter_typedef as typedef

    def __init__(w_self, w_rope, index=0):
        w_self.node = node = w_rope._node
        w_self.item_iter = rope.ItemIterator(node)
        w_self.index = index

registerimplementation(W_RopeIterObject)

def _is_generic(space, w_self, fun):
    l = w_self._node.length()
    if l == 0:
        return space.w_False
    iter = rope.ItemIterator(w_self._node)
    for i in range(l):
        if not fun(iter.nextchar()):
            return space.w_False
    return space.w_True
_is_generic._annspecialcase_ = "specialize:arg(2)"

_isspace = lambda c: c.isspace()
_isdigit = lambda c: c.isdigit()
_isalpha = lambda c: c.isalpha()
_isalnum = lambda c: c.isalnum()

def str_isspace__Rope(space, w_self):
    return _is_generic(space, w_self, _isspace)

def str_isdigit__Rope(space, w_self):
    return _is_generic(space, w_self, _isdigit)

def str_isalpha__Rope(space, w_self):
    return _is_generic(space, w_self, _isalpha)

def str_isalnum__Rope(space, w_self):
    return _is_generic(space, w_self, _isalnum)

def str_isupper__Rope(space, w_self):
    """Return True if all cased characters in S are uppercase and there is
at least one cased character in S, False otherwise."""
    l = w_self._node.length()

    if l == 0:
        return space.w_False
    cased = False
    iter = rope.ItemIterator(w_self._node)
    for idx in range(l):
        c = iter.nextchar()
        if c.islower():
            return space.w_False
        elif not cased and c.isupper():
            cased = True
    return space.newbool(cased)

def str_islower__Rope(space, w_self):
    """Return True if all cased characters in S are lowercase and there is
at least one cased character in S, False otherwise."""
    l = w_self._node.length()

    if l == 0:
        return space.w_False
    cased = False
    iter = rope.ItemIterator(w_self._node)
    for idx in range(l):
        c = iter.nextchar()
        if c.isupper():
            return space.w_False
        elif not cased and c.islower():
            cased = True
    return space.newbool(cased)

def str_istitle__Rope(space, w_self):
    """Return True if S is a titlecased string and there is at least one
character in S, i.e. uppercase characters may only follow uncased
characters and lowercase characters only cased ones. Return False
otherwise."""
    cased = False
    previous_is_cased = False

    iter = rope.ItemIterator(w_self._node)
    for pos in range(0, w_self._node.length()):
        ch = iter.nextchar()
        if ch.isupper():
            if previous_is_cased:
                return space.w_False
            previous_is_cased = True
            cased = True
        elif ch.islower():
            if not previous_is_cased:
                return space.w_False
            cased = True
        else:
            previous_is_cased = False

    return space.newbool(cased)

def _local_transform(node, transform):
    l = node.length()
    res = [' '] * l
    iter = rope.ItemIterator(node)
    for i in range(l):
        ch = iter.nextchar()
        res[i] = transform(ch)

    return W_RopeObject(rope.rope_from_charlist(res))
_local_transform._annspecialcase_ = "specialize:arg(1)"

def str_upper__Rope(space, w_self):
    return _local_transform(w_self._node, _upper)

def str_lower__Rope(space, w_self):
    return _local_transform(w_self._node, _lower)

def _swapcase(ch):
    if ch.isupper():
        o = ord(ch) + 32
        return chr(o)
    elif ch.islower():
        o = ord(ch) - 32
        return chr(o)
    else:
        return ch

def str_swapcase__Rope(space, w_self):
    return _local_transform(w_self._node, _swapcase)


def str_capitalize__Rope(space, w_self):
    node = w_self._node
    length = node.length()
    buffer = [' '] * length
    if length > 0:
        iter = rope.ItemIterator(node)
        ch = iter.nextchar()
        if ch.islower():
            o = ord(ch) - 32
            buffer[0] = chr(o)
        else:
            buffer[0] = ch

        for i in range(1, length):
            ch = iter.nextchar()
            if ch.isupper():
                o = ord(ch) + 32
                buffer[i] = chr(o)
            else:
                buffer[i] = ch
    else:
        return W_RopeObject.EMPTY

    return W_RopeObject(rope.rope_from_charlist(buffer))


def str_title__Rope(space, w_self):
    node = w_self._node
    length = node.length()
    buffer = [' '] * length
    prev_letter = ' '

    iter = rope.ItemIterator(node)
    for pos in range(0, length):
        ch = iter.nextchar()
        if not prev_letter.isalpha():
            buffer[pos] = _upper(ch)
        else:
            buffer[pos] = _lower(ch)

        prev_letter = buffer[pos]

    return W_RopeObject(rope.rope_from_charlist(buffer))

def str_split__Rope_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    selfnode = w_self._node
    maxsplit = space.int_w(w_maxsplit)
    res_w = [W_RopeObject(node)
                for node in rope.split_chars(selfnode, maxsplit)]
    return space.newlist(res_w)

def str_split__Rope_Rope_ANY(space, w_self, w_by, w_maxsplit=-1):
    maxsplit = space.int_w(w_maxsplit)
    selfnode = w_self._node
    bynode = w_by._node
    bylen = bynode.length()
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))
    res_w = [W_RopeObject(node)
                for node in rope.split(selfnode, bynode, maxsplit)]
    return space.newlist(res_w)


def str_rsplit__Rope_None_ANY(space, w_self, w_none, w_maxsplit=-1):
    selfnode = w_self._node
    maxsplit = space.int_w(w_maxsplit)
    res_w = [W_RopeObject(node)
                for node in rope.rsplit_chars(selfnode, maxsplit)]
    return space.newlist(res_w)


def str_rsplit__Rope_Rope_ANY(space, w_self, w_by, w_maxsplit=-1):
    # XXX works but flattens
    maxsplit = space.int_w(w_maxsplit)
    res_w = []
    value = w_self._node.flatten_string()
    end = len(value)
    by = w_by._node.flatten_string()
    bylen = len(by)
    if bylen == 0:
        raise OperationError(space.w_ValueError, space.wrap("empty separator"))

    while maxsplit != 0:
        next = value.rfind(by, 0, end)
        if next < 0:
            break
        res_w.append(space.wrap(value[next+bylen: end]))
        end = next
        maxsplit -= 1   # NB. if it's already < 0, it stays < 0

    res_w.append(space.wrap(value[:end]))
    res_w.reverse()
    return space.newlist(res_w)

def str_join__Rope_ANY(space, w_self, w_list):
    list_w = space.unpackiterable(w_list)
    size = len(list_w)

    if size == 0:
        return W_RopeObject.EMPTY
    if size == 1:
        w_s = list_w[0]
        # only one item,  return it if it's not a subclass of str
        if (space.is_w(space.type(w_s), space.w_str) or
            space.is_w(space.type(w_s), space.w_unicode)):
            return w_s

    self = w_self._node
    l = []
    for i in range(size):
        w_s = list_w[i]
        if not space.isinstance_w(w_s, space.w_str):
            if space.isinstance_w(w_s, space.w_unicode):
                w_u = space.call_function(space.w_unicode, w_self)
                return space.call_method(w_u, "join", space.newlist(list_w))
            raise operationerrfmt(
                space.w_TypeError,
                "sequence item %d: expected string, %s "
                "found", i, space.type(w_s).getname(space))
        assert isinstance(w_s, W_RopeObject)
        node = w_s._node
        l.append(node)
    try:
        return W_RopeObject(rope.join(self, l))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def str_rjust__Rope_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_arg = space.int_w(w_arg)
    selfnode = w_self._node
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("rjust() argument 2 must be a single character"))

    d = u_arg - selfnode.length()
    if d > 0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        resultnode = rope.concatenate(
                rope.multiply(rope.LiteralStringNode.PREBUILT[ord(fillchar)],
                              d),
                selfnode)
        return W_RopeObject(resultnode)
    else:
        return W_RopeObject(selfnode)

def str_ljust__Rope_ANY_ANY(space, w_self, w_arg, w_fillchar):
    u_arg = space.int_w(w_arg)
    selfnode = w_self._node
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("rjust() argument 2 must be a single character"))

    d = u_arg - selfnode.length()
    if d > 0:
        fillchar = fillchar[0]    # annotator hint: it's a single character
        resultnode = rope.concatenate(
                selfnode,
                rope.multiply(rope.LiteralStringNode.PREBUILT[ord(fillchar)],
                              d))
        return W_RopeObject(resultnode)
    else:
        return W_RopeObject(selfnode)

def _convert_idx_params(space, w_self, w_sub, w_start, w_end, upper_bound=False):
    self = w_self._node
    sub = w_sub._node

    if space.is_w(w_start, space.w_None):
        w_start = space.wrap(0)
    if space.is_w(w_end, space.w_None):
        w_end = space.len(w_self)
    if upper_bound:
        start = slicetype.adapt_bound(space, self.length(), w_start)
        end = slicetype.adapt_bound(space, self.length(), w_end)
    else:
        start = slicetype.adapt_lower_bound(space, self.length(), w_start)
        end = slicetype.adapt_lower_bound(space, self.length(), w_end)

    return (self, sub, start, end)
_convert_idx_params._annspecialcase_ = 'specialize:arg(5)'

def contains__Rope_Rope(space, w_self, w_sub):
    self = w_self._node
    sub = w_sub._node
    return space.newbool(rope.find(self, sub) >= 0)

def str_find__Rope_Rope_ANY_ANY(space, w_self, w_sub, w_start, w_end):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = rope.find(self, sub, start, end)
    return wrapint(space, res)

def str_rfind__Rope_Rope_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    # XXX works but flattens
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    self = self.flatten_string()
    sub = sub.flatten_string()
    res = self.rfind(sub, start, end)
    return wrapint(space, res)

def str_partition__Rope_Rope(space, w_self, w_sub):
    self = w_self._node
    sub = w_sub._node
    if not sub.length():
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    pos = rope.find(self, sub)
    if pos == -1:
        return space.newtuple([w_self, W_RopeObject.EMPTY,
                               W_RopeObject.EMPTY])
    else:
        return space.newtuple(
            [W_RopeObject(rope.getslice_one(self, 0, pos)),
             w_sub,
             W_RopeObject(rope.getslice_one(self, pos + sub.length(),
                                            self.length()))])

def str_rpartition__Rope_Rope(space, w_self, w_sub):
    # XXX works but flattens
    self = w_self._node
    sub = w_sub._node
    if not sub.length():
        raise OperationError(space.w_ValueError,
                             space.wrap("empty separator"))
    flattened_self = self.flatten_string()
    flattened_sub = sub.flatten_string()
    pos = flattened_self.rfind(flattened_sub)
    if pos == -1:
        return space.newtuple([W_RopeObject.EMPTY, W_RopeObject.EMPTY, w_self])
    else:
        return space.newtuple(
            [W_RopeObject(rope.getslice_one(self, 0, pos)),
             w_sub,
             W_RopeObject(rope.getslice_one(self, pos + sub.length(),
                                            self.length()))])

def str_index__Rope_Rope_ANY_ANY(space, w_self, w_sub, w_start, w_end):

    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    res = rope.find(self, sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.index"))

    return wrapint(space, res)


def str_rindex__Rope_Rope_ANY_ANY(space, w_self, w_sub, w_start, w_end):
    (self, sub, start, end) =  _convert_idx_params(space, w_self, w_sub, w_start, w_end)
    # XXX works but flattens
    self = self.flatten_string()
    sub = sub.flatten_string()
    res = self.rfind(sub, start, end)
    if res < 0:
        raise OperationError(space.w_ValueError,
                             space.wrap("substring not found in string.rindex"))

    return wrapint(space, res)


def str_replace__Rope_Rope_Rope_ANY(space, w_self, w_sub, w_by, w_maxsplit=-1):

    node = w_self._node
    length = node.length()
    sub = w_sub._node
    by = w_by._node
    maxsplit = space.int_w(w_maxsplit)
    if maxsplit == 0:
        return w_self.create_if_subclassed()

    if not sub.length():
        upper = node.length()
        if maxsplit > 0 and maxsplit < upper + 2:
            upper = maxsplit - 1
            assert upper >= 0
        substrings = [by]
        iter = rope.ItemIterator(node)
        for i in range(upper):
            substrings.append(iter.nextrope())
            substrings.append(by)
        substrings.append(rope.getslice_one(node, upper, length))
        try:
            return W_RopeObject(rope.rebalance(substrings))
        except OverflowError:
            raise OperationError(space.w_OverflowError,
                                 space.wrap("string too long"))
    substrings = rope.split(node, sub, maxsplit)
    if not substrings:
        return w_self.create_if_subclassed()
    try:
        return W_RopeObject(rope.join(by, substrings))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))


def _contains(i, string):
    return chr(i) in string

def str_strip__Rope_Rope(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, True, True,
                                   _contains, w_chars._node.flatten_string()))

def str_strip__Rope_None(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, left=True, right=True))

def str_rstrip__Rope_Rope(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, False, True,
                                   _contains, w_chars._node.flatten_string()))

def str_rstrip__Rope_None(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, False, True))

def str_lstrip__Rope_Rope(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, True, False,
                                   _contains, w_chars._node.flatten_string()))

def str_lstrip__Rope_None(space, w_self, w_chars):
    return W_RopeObject(rope.strip(w_self._node, left=True, right=False))


def str_center__Rope_ANY_ANY(space, w_self, w_arg, w_fillchar):
    node = w_self._node
    length = node.length()
    arg  = space.int_w(w_arg)
    fillchar = space.str_w(w_fillchar)
    if len(fillchar) != 1:
        raise OperationError(space.w_TypeError,
            space.wrap("center() argument 2 must be a single character"))

    d = arg - length
    if d>0:
        offset = d//2 + (d & arg & 1)
        fillcharnode = rope.LiteralStringNode.PREBUILT[ord(fillchar)]
        pre = rope.multiply(fillcharnode, offset)
        post = rope.multiply(fillcharnode, (d - offset))
        centered = rope.rebalance([pre, node, post])
        return W_RopeObject(centered)
    else:
        return w_self.create_if_subclassed()

def str_count__Rope_Rope_ANY_ANY(space, w_self, w_arg, w_start, w_end):
    selfnode  = w_self._node
    length = selfnode.length()
    argnode   = w_arg._node

    u_start = slicetype.adapt_bound(space, length, w_start)
    u_end = slicetype.adapt_bound(space, length, w_end)
    assert u_start >= 0
    assert u_end >= 0
    iter = rope.FindIterator(selfnode, argnode, u_start, u_end)
    i = 0
    while 1:
        try:
            index = iter.next()
        except StopIteration:
            break
        i += 1
    return wrapint(space, i)


def str_endswith__Rope_Rope_ANY_ANY(space, w_self, w_suffix, w_start, w_end):
    (self, suffix, start, end) = _convert_idx_params(space, w_self,
                                                     w_suffix, w_start, w_end,
                                                     True)
    return space.newbool(rope.endswith(self, suffix, start, end))

def str_endswith__Rope_Tuple_ANY_ANY(space, w_self, w_suffixes, w_start, w_end):
    (self, _, start, end) = _convert_idx_params(space, w_self,
                                                W_RopeObject.EMPTY, w_start,
                                                w_end, True)
    for w_suffix in space.fixedview(w_suffixes):
        if space.isinstance_w(w_suffix, space.w_unicode):
            w_u = space.call_function(space.w_unicode, w_self)
            return space.call_method(w_u, "endswith", w_suffixes, w_start,
                                     w_end)
        suffix = rope_w(space, w_suffix)
        if rope.endswith(self, suffix, start, end):
            return space.w_True
    return space.w_False


def str_startswith__Rope_Rope_ANY_ANY(space, w_self, w_prefix, w_start, w_end):
    (self, prefix, start, end) = _convert_idx_params(space, w_self,
                                                     w_prefix, w_start, w_end,
                                                     True)
    return space.newbool(rope.startswith(self, prefix, start, end))

def str_startswith__Rope_Tuple_ANY_ANY(space, w_self, w_prefixes, w_start, w_end):
    (self, _, start, end) = _convert_idx_params(space, w_self, W_RopeObject.EMPTY,
                                                  w_start, w_end, True)
    for w_prefix in space.fixedview(w_prefixes):
        if space.isinstance_w(w_prefix, space.w_unicode):
            w_u = space.call_function(space.w_unicode, w_self)
            return space.call_method(w_u, "startswith", w_prefixes, w_start,
                                     w_end)
        prefix = rope_w(space, w_prefix)
        if rope.startswith(self, prefix, start, end):
            return space.w_True
    return space.w_False


def _tabindent(node, tabsize):
    "calculates distance after the token to the next tabstop"
    length = node.length()
    distance = tabsize
    if length:
        distance = 0
        iter = rope.ReverseItemIterator(node)

        while 1:
            # no sophisticated linebreak support now
            # '\r' just for passing adapted CPython test
            try:
                char = iter.nextint()
            except StopIteration:
                break
            if char == ord("\n") or char == ord("\r"):
                break
            distance += 1

        #the same like distance = len(u_token) - (offset + 1)
        distance = (tabsize - distance) % tabsize
        if distance == 0:
            return tabsize

    return distance


def str_expandtabs__Rope_ANY(space, w_self, w_tabsize):
    node = w_self._node
    length = node.length()
    if length == 0:
        return W_RopeObject.EMPTY
    tabsize  = space.int_w(w_tabsize)

    splitted = rope.split(node, rope.LiteralStringNode.PREBUILT[ord("\t")])
    last = splitted[0]
    expanded = [last]
    for i in range(1, len(splitted)):
        expanded.append(rope.multiply(rope.LiteralStringNode.PREBUILT[ord(" ")],
                                      _tabindent(last, tabsize)))
        last = splitted[i]
        expanded.append(last)
    try:
        return W_RopeObject(rope.rebalance(expanded))
    except OverflowError:
        raise OperationError(space.w_OverflowError, space.wrap('new string is too long'))


def str_splitlines__Rope_ANY(space, w_self, w_keepends):
    keepends = bool(space.int_w(w_keepends))  # truth value, but type checked
    node = w_self._node
    return space.newlist(
        [W_RopeObject(n) for n in rope.splitlines(node, keepends)])

def str_zfill__Rope_ANY(space, w_self, w_width):
    node = w_self._node
    length = node.length()
    width = space.int_w(w_width)

    if length >= width:
        return w_self.create_if_subclassed()
    zero = rope.LiteralStringNode.PREBUILT[ord("0")]
    if length == 0:
        return W_RopeObject(rope.multiply(zero, width))

    middle = width - length
    firstchar = node.getchar(0)
    if length > 0 and (firstchar == '+' or firstchar == '-'):
        return W_RopeObject(rope.rebalance(
            [rope.LiteralStringNode.PREBUILT[ord(firstchar)],
             rope.multiply(zero, middle),
             rope.getslice_one(node, 1, length)]))
    else:
        middle = width - length
        return W_RopeObject(rope.concatenate(
            rope.multiply(zero, middle), node))

def hash__Rope(space, w_str):
    return wrapint(space, rope.hash_rope(w_str._node))

def lt__Rope_Rope(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) < 0)

def le__Rope_Rope(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) <= 0)

def _eq(w_str1, w_str2):
    result = rope.eq(w_str1._node, w_str2._node)
    return result

def eq__Rope_Rope(space, w_str1, w_str2):
    return space.newbool(_eq(w_str1, w_str2))

def ne__Rope_Rope(space, w_str1, w_str2):
    return space.newbool(not _eq(w_str1, w_str2))

def gt__Rope_Rope(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) > 0)

def ge__Rope_Rope(space, w_str1, w_str2):
    n1 = w_str1._node
    n2 = w_str2._node
    return space.newbool(rope.compare(n1, n2) >= 0)

def getitem__Rope_ANY(space, w_str, w_index):
    ival = space.getindex_w(w_index, space.w_IndexError, "string index")
    node = w_str._node
    slen = node.length()
    if ival < 0:
        ival += slen
    if ival < 0 or ival >= slen:
        raise OperationError(space.w_IndexError,
                             space.wrap("string index out of range"))
    return wrapchar(space, node.getchar(ival))

def getitem__Rope_Slice(space, w_str, w_slice):
    node = w_str._node
    length = node.length()
    start, stop, step, sl = w_slice.indices4(space, length)
    if sl == 0:
        return W_RopeObject.EMPTY
    return W_RopeObject(rope.getslice(node, start, stop, step, sl))

def getslice__Rope_ANY_ANY(space, w_str, w_start, w_stop):
    node = w_str._node
    length = node.length()
    start, stop = normalize_simple_slice(space, length, w_start, w_stop)
    sl = stop - start
    if sl == 0:
        return W_RopeObject.EMPTY
    return W_RopeObject(rope.getslice(node, start, stop, 1, sl))

def mul_string_times(space, w_str, w_times):
    try:
        mul = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if mul <= 0:
        return W_RopeObject.EMPTY
    node = w_str._node
    try:
        return W_RopeObject(rope.multiply(node, mul))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def mul__Rope_ANY(space, w_str, w_times):
    return mul_string_times(space, w_str, w_times)

def mul__ANY_Rope(space, w_times, w_str):
    return mul_string_times(space, w_str, w_times)

def add__Rope_Rope(space, w_left, w_right):
    right = w_right._node
    left = w_left._node
    try:
        return W_RopeObject(rope.concatenate(left, right))
    except OverflowError:
        raise OperationError(space.w_OverflowError,
                             space.wrap("string too long"))

def len__Rope(space, w_str):
    return space.wrap(w_str._node.length())

def str__Rope(space, w_str):
    if type(w_str) is W_RopeObject:
        return w_str
    return W_RopeObject(w_str._node)

def iter__Rope(space, w_str):
    return W_RopeIterObject(w_str)

def ord__Rope(space, w_str):
    node = w_str._node
    if node.length() != 1:
        raise operationerrfmt(
            space.w_TypeError,
            "ord() expected a character, but string "
            "of length %d found", node.length())
    return space.wrap(node.getint(0))

def getnewargs__Rope(space, w_str):
    return space.newtuple([W_RopeObject(w_str._node)])

def repr__Rope(space, w_str):
    node = w_str._node
    length = node.length()

    i = 0
    buf = [' '] * (length * 4 + 2) # safely overallocate

    quote = "'"
    if (rope.find_int(node, ord(quote)) != -1 and
        rope.find_int(node, ord('"')) == -1):
        quote = '"'

    buf[0] = quote

    iter = rope.ItemIterator(node)
    while 1:
        try:
            c = iter.nextchar()
            i += 1
        except StopIteration:
            break
        bs_char = None # character quoted by backspace

        if c == '\\' or c == quote:
            bs_char = c
        elif c == '\t': bs_char = 't'
        elif c == '\r': bs_char = 'r'
        elif c == '\n': bs_char = 'n'
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            buf[i] = '\\'
            i += 1
            buf[i] = 'x'
            i += 1
            buf[i] = "0123456789abcdef"[n>>4]
            i += 1
            buf[i] = "0123456789abcdef"[n&0xF]
        else:
            buf[i] = c

        if bs_char is not None:
            buf[i] = '\\'
            i += 1
            buf[i] = bs_char

    i += 1
    buf[i] = quote

    return W_RopeObject(rope.rope_from_charlist(buf[:i+1]))

def str_translate__Rope_ANY_ANY(space, w_string, w_table, w_deletechars=''):
    """charfilter - unicode handling is not implemented

    Return a copy of the string where all characters occurring
    in the optional argument deletechars are removed, and the
    remaining characters have been mapped through the given translation table,
    which must be a string of length 256"""

    if space.is_w(w_table, space.w_None):
        table = DEFAULT_NOOP_TABLE
    else:
        table = space.bufferstr_w(w_table)
        if len(table) != 256:
            raise OperationError(
                space.w_ValueError,
                space.wrap("translation table must be 256 characters long"))

    node = w_string._node
    chars = []
    iter = rope.ItemIterator(node)
    while 1:
        try:
            c = iter.nextchar()
            w_char = W_RopeObject.PREBUILT[ord(c)]
            if not space.is_true(space.contains(w_deletechars, w_char)):
                 chars.append(table[ord(c)])
        except StopIteration:
            break
    return W_RopeObject(rope.rope_from_charlist(chars))

def str_decode__Rope_ANY_ANY(space, w_string, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
        getdefaultencoding
    if space.config.objspace.std.withropeunicode:
        from pypy.objspace.std.ropeunicodeobject import decode_string
    else:
        from pypy.objspace.std.unicodetype import decode_object as decode_string
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    if encoding is None:
        encoding = getdefaultencoding(space)
    return decode_string(space, w_string, encoding, errors)

def str_encode__Rope_ANY_ANY(space, w_string, w_encoding=None, w_errors=None):
    from pypy.objspace.std.unicodetype import _get_encoding_and_errors, \
        encode_object
    encoding, errors = _get_encoding_and_errors(space, w_encoding, w_errors)
    return encode_object(space, w_string, encoding, errors)

def buffer__Rope(space, w_string):
    from pypy.interpreter.buffer import StringBuffer
    value = w_string._node.flatten_string()      # XXX inefficient
    return space.wrap(StringBuffer(value))


# methods of the iterator

def iter__RopeIter(space, w_ropeiter):
    return w_ropeiter

def next__RopeIter(space, w_ropeiter):
    if w_ropeiter.node is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    try:
        char = w_ropeiter.item_iter.nextchar()
        w_item = wrapchar(space, char)
    except StopIteration:
        w_ropeiter.node = None
        w_ropeiter.char_iter = None
        raise OperationError(space.w_StopIteration, space.w_None)
    w_ropeiter.index += 1
    return w_item

# XXX __length_hint__()
##def len__RopeIter(space,  w_ropeiter):
##    if w_ropeiter.node is None:
##        return wrapint(space, 0)
##    index = w_ropeiter.index
##    length = w_ropeiter.node.length()
##    result = length - index
##    if result < 0:
##        return wrapint(space, 0)
##    return wrapint(space, result)

# register all methods
from pypy.objspace.std import stringtype
register_all(vars(), stringtype)
