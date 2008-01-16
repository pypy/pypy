class UnionType(type):
    pass

class Union(object):
    __metaclass__ = UnionType

class ArgumentError(Exception):
    pass

def dummyfunc(*args, **kwargs):
    return None

addressof = dummyfunc
alignment = dummyfunc
resize = dummyfunc
_memmove_addr = dummyfunc
_memset_addr = dummyfunc
_string_at_addr = dummyfunc
_cast_addr = dummyfunc

