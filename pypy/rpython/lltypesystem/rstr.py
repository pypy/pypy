from pypy.rpython.rstr import AbstractStringRepr, STR, AbstractStringIteratorRepr, \
        ll_strconcat
from pypy.rpython.lltypesystem.lltype import malloc, GcStruct, Ptr, Signed

class StringRepr(AbstractStringRepr):

    lowleveltype = Ptr(STR)

    def __init__(self, *args):
        AbstractStringRepr.__init__(self, *args)
        self.ll_strip = ll_strip
        self.ll_upper = ll_upper
        self.ll_lower = ll_lower
        self.ll_join = ll_join

    def make_iterator_repr(self):
        return string_iterator_repr

    def can_ll_be_null(self, s_value):
        if self is string_repr:
            return s_value.can_be_none()
        else:
            return True     # for CharRepr/UniCharRepr subclasses,
                            # where NULL is always valid: it is chr(0)

def ll_strip(s, ch, left, right):
    s_len = len(s.chars)
    if s_len == 0:
        return emptystr
    lpos = 0
    rpos = s_len - 1
    if left:
        while lpos < rpos and s.chars[lpos] == ch:
            lpos += 1
    if right:
        while lpos < rpos and s.chars[rpos] == ch:
            rpos -= 1
    r_len = rpos - lpos + 1
    result = malloc(STR, r_len)
    i = 0
    j = lpos
    while i < r_len:
        result.chars[i] = s.chars[j]
        i += 1
        j += 1
    return result

def ll_upper(s):
    s_chars = s.chars
    s_len = len(s_chars)
    if s_len == 0:
        return emptystr
    i = 0
    result = malloc(STR, s_len)
    while i < s_len:
        ch = s_chars[i]
        if 'a' <= ch <= 'z':
            ch = chr(ord(ch) - 32)
        result.chars[i] = ch
        i += 1
    return result

def ll_lower(s):
    s_chars = s.chars
    s_len = len(s_chars)
    if s_len == 0:
        return emptystr
    i = 0
    result = malloc(STR, s_len)
    while i < s_len:
        ch = s_chars[i]
        if 'A' <= ch <= 'Z':
            ch = chr(ord(ch) + 32)
        result.chars[i] = ch
        i += 1
    return result

def ll_join(s, length, items):
    s_chars = s.chars
    s_len = len(s_chars)
    num_items = length
    if num_items == 0:
        return emptystr
    itemslen = 0
    i = 0
    while i < num_items:
        itemslen += len(items[i].chars)
        i += 1
    result = malloc(STR, itemslen + s_len * (num_items - 1))
    res_chars = result.chars
    res_index = 0
    i = 0
    item_chars = items[i].chars
    item_len = len(item_chars)
    j = 0
    while j < item_len:
        res_chars[res_index] = item_chars[j]
        j += 1
        res_index += 1
    i += 1
    while i < num_items:
        j = 0
        while j < s_len:
            res_chars[res_index] = s_chars[j]
            j += 1
            res_index += 1

        item_chars = items[i].chars
        item_len = len(item_chars)
        j = 0
        while j < item_len:
            res_chars[res_index] = item_chars[j]
            j += 1
            res_index += 1
        i += 1
    return result

string_repr = StringRepr()

emptystr = string_repr.convert_const("")


class StringIteratorRepr(AbstractStringIteratorRepr):

    lowleveltype = Ptr(GcStruct('stringiter',
                                ('string', string_repr.lowleveltype),
                                ('index', Signed)))

    def __init__(self):
        self.ll_striter = ll_striter
        self.ll_strnext = ll_strnext

def ll_striter(string):
    iter = malloc(string_iterator_repr.lowleveltype.TO)
    iter.string = string
    iter.index = 0
    return iter

def ll_strnext(iter):
    chars = iter.string.chars
    index = iter.index
    if index >= len(chars):
        raise StopIteration
    iter.index = index + 1
    return chars[index]

string_iterator_repr = StringIteratorRepr()


# these should be in rclass, but circular imports prevent (also it's
# not that insane that a string constant is built in this file).

instance_str_prefix = string_repr.convert_const("<")
instance_str_suffix = string_repr.convert_const(" object>")

list_str_open_bracket = string_repr.convert_const("[")
list_str_close_bracket = string_repr.convert_const("]")
list_str_sep = string_repr.convert_const(", ")
