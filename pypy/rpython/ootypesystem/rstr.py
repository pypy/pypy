from pypy.rpython.error import TyperError
from pypy.rpython.rstr import AbstractStringRepr,AbstractCharRepr,\
     AbstractUniCharRepr, AbstractStringIteratorRepr,\
     AbstractLLHelpers
from pypy.rpython.lltypesystem.lltype import Ptr, Char, UniChar
from pypy.rpython.ootypesystem import ootype

# TODO: investigate if it's possibile and it's worth to concatenate a
# String and a Char directly without passing to Char-->String
# conversion

class StringRepr(AbstractStringRepr):
    """
    Some comments about the state of ootype strings at the end of Tokyo sprint

    What was accomplished:
    - The rstr module was split in an lltype and ootype version.
    - There is the beginnings of a String type in ootype.
    - The runtime representation of Strings is a subclass of the builtin str.
      The idea is that this saves us from boilerplate code implementing the
      builtin str methods.

    Nothing more was done because of lack of time and paralysis in the face
    of too many problems. Among other things, to write any meaningful tests
    we first need conversion from Chars to Strings (because
    test_llinterp.interpret won't accept strings as arguments). We will need a
    new low-level operation (convert_char_to_oostring or some such) for this.
    """

    lowleveltype = ootype.String

    def __init__(self, *args):
        AbstractStringRepr.__init__(self, *args)
        self.ll = LLHelpers

    def convert_const(self, value):
        if value is None:
            return ootype.String._null
        if not isinstance(value, str):
            raise TyperError("not a str: %r" % (value,))
        return ootype.make_string(value)

    def make_iterator_repr(self):
        return string_iterator_repr

    def _list_length_items(self, hop, v_lst, LIST):
        # ootypesystem list has a different interface that
        # lltypesystem list, so we don't need to calculate the lenght
        # here and to pass the 'items' array. Let's pass the list
        # itself and let LLHelpers.join to manipulate it directly.
        c_length = hop.inputconst(ootype.Void, None)
        return c_length, v_lst


class CharRepr(AbstractCharRepr, StringRepr):
    lowleveltype = Char

class UniCharRepr(AbstractUniCharRepr):
    lowleveltype = UniChar

class LLHelpers(AbstractLLHelpers):

    def ll_chr2str(ch):
        return ootype.oostring(ch)

    def ll_char_mul(ch, times):
        buf = ootype.new(ootype.StringBuilder)
        buf.ll_allocate(times)
        i = 0
        while i<times:
            buf.ll_append_char(ch)
            i+= 1
        return buf.ll_build()

    def ll_streq(s1, s2):
        if s1 is None:
            return s2 is None
        return s1.ll_streq(s2)

    def ll_strcmp(s1, s2):
        if not s1 and not s2:
            return True
        if not s1 or not s2:
            return False
        return s1.ll_strcmp(s2)

    def ll_join(s, length_dummy, lst):
        length = lst.ll_length()
        buf = ootype.new(ootype.StringBuilder)

        # TODO: check if it's worth of preallocating the buffer with
        # the exact length
##        itemslen = 0
##        i = 0
##        while i < length:
##            itemslen += lst.ll_getitem_fast(i).ll_strlen()
##            i += 1
##        resultlen = itemslen + s.ll_strlen()*(length-1)
##        buf.ll_allocate(resultlen)

        i = 0
        while i < length-1:
            item = lst.ll_getitem_fast(i)
            buf.ll_append(item)
            buf.ll_append(s)
            i += 1
        if length > 0:
            lastitem = lst.ll_getitem_fast(i)
            buf.ll_append(lastitem)
        return buf.ll_build()

    def ll_join_chars(length_dummy, lst):
        buf = ootype.new(ootype.StringBuilder)
        length = lst.ll_length()
        buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append_char(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()

    def ll_join_strs(length_dummy, lst):
        buf = ootype.new(ootype.StringBuilder)
        length = lst.ll_length()
        #buf.ll_allocate(length)
        i = 0
        while i < length:
            buf.ll_append(lst.ll_getitem_fast(i))
            i += 1
        return buf.ll_build()


def add_helpers():
    dic = {}
    for name, meth in ootype.String._GENERIC_METHODS.iteritems():
        if name in LLHelpers.__dict__:
            continue
        n_args = len(meth.ARGS)
        args = ', '.join(['arg%d' % i for i in range(n_args)])
        code = """
def %s(obj, %s):
    return obj.%s(%s)
""" % (name, args, name, args)
        exec code in dic
        setattr(LLHelpers, name, staticmethod(dic[name]))

add_helpers()
del add_helpers


string_repr = StringRepr()
char_repr = CharRepr()
unichar_repr = UniCharRepr()
char_repr.ll = LLHelpers
unichar_repr.ll = LLHelpers
emptystr = string_repr.convert_const("")

class StringIteratorRepr(AbstractStringIteratorRepr):
    lowleveltype = ootype.Record({'string': string_repr.lowleveltype,
                                  'index': ootype.Signed})

    def __init__(self):
        self.ll_striter = ll_striter
        self.ll_strnext = ll_strnext

def ll_striter(string):
    iter = ootype.new(string_iterator_repr.lowleveltype)
    iter.string = string
    iter.index = 0
    return iter

def ll_strnext(iter):
    string = iter.string    
    index = iter.index
    if index >= string.ll_strlen():
        raise StopIteration
    iter.index = index + 1
    return string.ll_stritem_nonneg(index)

string_iterator_repr = StringIteratorRepr()

