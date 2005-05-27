from pypy.annotation.model import SomeBool
from pypy.rpython.lltype import Bool
from pypy.rpython.rtyper import receive


class __extend__(SomeBool):

    def rtype_is_true(s_bool):
        v_bool = receive(Bool, arg=0)
        return v_bool
