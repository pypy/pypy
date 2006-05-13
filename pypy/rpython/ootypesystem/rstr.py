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


class CharRepr(AbstractCharRepr, StringRepr):
    lowleveltype = Char

class UniCharRepr(AbstractUniCharRepr):
    lowleveltype = UniChar

class LLHelpers(AbstractLLHelpers):
    def ll_stritem_nonneg(s, i):
        return s.ll_stritem_nonneg(i)

    def ll_strlen(s):
        return s.ll_strlen()

    def ll_strconcat(s1, s2):
        return s1.ll_strconcat(s2)

    def ll_chr2str(ch):
        return ootype.oostring(ch)

string_repr = StringRepr()
char_repr = CharRepr()
unichar_repr = UniCharRepr()
char_repr.ll = LLHelpers
unichar_repr.ll = LLHelpers

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

