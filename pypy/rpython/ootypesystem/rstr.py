from pypy.rpython.rstr import AbstractStringRepr, STR, AbstractStringIteratorRepr
from pypy.rpython.lltypesystem.lltype import Ptr
from pypy.rpython.ootypesystem.ootype import Signed, Record, String, make_string

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

    lowleveltype = String

    def convert_const(self, value):
        # XXX what do we do about null strings?
        #if value is None:
        #    return nullptr(STR)
        if not isinstance(value, str):
            raise TyperError("not a str: %r" % (value,))
        return make_string(value)

    def make_iterator_repr(self):
        return string_iterator_repr

string_repr = StringRepr()

class StringIteratorRepr(AbstractStringIteratorRepr):

    lowleveltype = Record({'string': string_repr.lowleveltype, 'index': Signed})

string_iterator_repr = StringIteratorRepr
