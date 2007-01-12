
from pypy.rpython.rgeneric import AbstractGenericCallableRepr
from pypy.rpython.lltypesystem.lltype import Ptr, FuncType

class GenericCallableRepr(AbstractGenericCallableRepr):
    def create_low_leveltype(self):
        l_args = [r_arg.lowleveltype for r_arg in self.args_r]
        l_retval = self.r_result.lowleveltype
        return Ptr(FuncType(l_args, l_retval))
