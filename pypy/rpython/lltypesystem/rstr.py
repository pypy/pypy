from pypy.rpython.rstr import string_repr, StringRepr, STR, AbstractStringIteratorRepr, \
        ll_strconcat, instance_str_prefix, instance_str_suffix, list_str_open_bracket, ll_join, list_str_sep, list_str_close_bracket
from pypy.rpython.lltypesystem.lltype import malloc, GcStruct, Ptr, Signed

class __extend__(StringRepr):

    lowleveltype = Ptr(STR)

    def make_iterator_repr(self):
        return string_iterator_repr


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
