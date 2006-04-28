from pypy.rpython.rstr import AbstractStringRepr, STR, AbstractStringIteratorRepr
from pypy.rpython.lltypesystem.lltype import Ptr
from pypy.rpython.ootypesystem.ootype import Signed, Record

class StringRepr(AbstractStringRepr):

    lowleveltype = Ptr(STR)

    def make_iterator_repr(self):
        return string_iterator_repr

string_repr = StringRepr()

class StringIteratorRepr(AbstractStringIteratorRepr):

    lowleveltype = Record({'string': string_repr.lowleveltype, 'index': Signed})

string_iterator_repr = StringIteratorRepr
