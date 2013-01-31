
from rpython.rtyper.rgeneric import AbstractGenericCallableRepr
from rpython.rtyper.ootypesystem import ootype

class GenericCallableRepr(AbstractGenericCallableRepr):
    def create_low_leveltype(self):
        l_args = [r_arg.lowleveltype for r_arg in self.args_r]
        l_retval = self.r_result.lowleveltype
        return ootype.StaticMethod(l_args, l_retval)
