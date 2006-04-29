from pypy.rpython.rstr import AbstractStringRepr, STR, AbstractStringIteratorRepr
from pypy.rpython.lltypesystem.lltype import Ptr
from pypy.rpython.ootypesystem.ootype import Signed, Record, String, make_string

class StringRepr(AbstractStringRepr):

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
