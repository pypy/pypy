from pypy.rpython.rstr import string_repr, StringRepr, STR, AbstractStringIteratorRepr
from pypy.rpython.lltypesystem.lltype import Ptr
from pypy.rpython.ootypesystem.ootype import Signed, Record

class __extend__(StringRepr):

    lowleveltype = Ptr(STR)

    def make_iterator_repr(self):
        return string_iterator_repr


class StringIteratorRepr(AbstractStringIteratorRepr):

    lowleveltype = Record({'string': string_repr.lowleveltype, 'index': Signed})

string_iterator_repr = StringIteratorRepr
