from pypy.rpython.ootypesystem.ootype import oostring

def from_rstr(rs):
    if not rs:   # null pointer
        return None
    else:
        return "".join([rs.ll_stritem_nonneg(i) for i in range(rs.ll_strlen())])

def to_rstr(s):
    return oostring(s, -1)
