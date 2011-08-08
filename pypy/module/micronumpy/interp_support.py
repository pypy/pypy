from pypy.rlib.rstruct.runpack import runpack
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec


FLOAT_SIZE = rffi.sizeof(lltype.Float)

@unwrap_spec(s=str)
def fromstring(space, s):
    from pypy.module.micronumpy.interp_numarray import SingleDimArray
    length = len(s)

    if length % FLOAT_SIZE == 0:
        number = length/FLOAT_SIZE
    else:
        raise OperationError(space.w_ValueError, space.wrap(
            "string length %d not divisable by %d" % (length, FLOAT_SIZE)))

    a = SingleDimArray(number)

    start = 0
    end = FLOAT_SIZE
    i = 0
    while i < number:
        part = s[start:end]
        a.storage[i] = runpack('d', part)
        i += 1
        start += FLOAT_SIZE
        end += FLOAT_SIZE

    return space.wrap(a)

class Signature(object):
    def __init__(self):
        self.transitions = {}

    def transition(self, target):
        if target in self.transitions:
            return self.transitions[target]
        self.transitions[target] = new = Signature()
        return new