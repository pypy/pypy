from pypy.rpython import lltype



class Address(object):
    pass


supported_access_types = {"signed":    lltype.Signed,
                          "unsigned":  lltype.Unsigned,
                          "char":      lltype.Char,
                          "address":   Address,
                          }

NULL = Address()

def raw_malloc(size):
    pass

def raw_free(addr):
    pass

def raw_memcopy(addr1, addr2, size):
    pass


