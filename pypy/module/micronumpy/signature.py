from pypy.rlib.objectmodel import r_dict, compute_identity_hash
from pypy.rlib.rarithmetic import intmask


def components_eq(lhs, rhs):
    if len(lhs) != len(rhs):
        return False
    for i in range(len(lhs)):
        v1, v2 = lhs[i], rhs[i]
        if type(v1) is not type(v2) or not v1.eq(v2):
            return False
    return True

def components_hash(components):
    res = 0x345678
    for component in components:
        res = intmask((1000003 * res) ^ component.hash())
    return res

class BaseSignature(object):
    def eq(self, other):
        return self is other

    def hash(self):
        return compute_identity_hash(self)

class Signature(BaseSignature):
    _known_sigs = r_dict(components_eq, components_hash)

    def __init__(self, components):
        self.components = components

    @staticmethod
    def find_sig(components):
        return Signature._known_sigs.setdefault(components, Signature(components))

class Call1(BaseSignature):
    _immutable_fields_ = ["func"]

    def __init__(self, func):
        self.func = func

class Call2(BaseSignature):
    _immutable_fields_ = ["func"]

    def __init__(self, func):
        self.func = func