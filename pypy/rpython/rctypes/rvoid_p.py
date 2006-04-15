from pypy.rpython.rctypes.rmodel import CTypesValueRepr


class CVoidPRepr(CTypesValueRepr):
    pass  # No operations supported on c_void_p instances so far
