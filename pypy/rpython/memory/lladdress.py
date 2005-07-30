from pypy.rpython import lltype

class Address(object):
    def __new__(cls, intaddress=0):
        if intaddress == 0:
            null = cls.__dict__.get("NULL")
            if null is not None:
                return null
            cls.NULL = object.__new__(cls)
            return cls.NULL
        else:
            return object.__new__(cls)

    def __init__(self, intaddress=0):
        self.intaddress = intaddress

    def __add__(self, offset):
        assert isinstance(offset, int)
        return Address(self.intaddress + offset)

    def __sub__(self, other):
        if isinstance(other, int):
            return Address(self.intaddress + offset)
        else:
            return self.intaddress - other.intaddress

    def __cmp__(self, other):
        return cmp(self.intaddress, other.intaddress)

NULL = Address()

supported_access_types = {"signed":    lltype.Signed,
                          "unsigned":  lltype.Unsigned,
                          "char":      lltype.Char,
                          "address":   Address,
                          }

def raw_malloc(size):
    pass

def raw_free(addr):
    pass

def raw_memcopy(addr1, addr2, size):
    pass


