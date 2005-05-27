from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeFloat, SomeInteger, SomeBool
from pypy.rpython.lltype import Signed, Unsigned, Bool
from pypy.rpython.rtyper import peek_at_result_annotation, receive, direct_op
from pypy.rpython.rtyper import TyperError


class __extend__(pairtype(SomeFloat, SomeFloat)):
    pass


class __extend__(pairtype(SomeFloat, SomeInteger)):
    pass


class __extend__(SomeFloat):
    pass
