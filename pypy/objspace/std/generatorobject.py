from pypy.objspace.std.objspace import *
from generatortype import W_GeneratorType

class W_GeneratorObject(W_Object):
    statictype = W_GeneratorType

    def __init__(self, space, frame):
        self.frame = frame
        self.running = 0

registerimplementation(W_GeneratorObject)

def next__Generator(space, w_gen):
    if w_gen.running:
        raise OperationError(space.w_ValueError,
                             space.wrap("generator already executing"))
    ec = space.getexecutioncontext()

    w_gen.running = 1
    try:
        w_ret = ec.eval_frame(w_gen.frame)
    finally:
        w_gen.running = 0

    return w_ret


def iter__Generator(space, w_gen):
    return w_gen

register_all(vars())
