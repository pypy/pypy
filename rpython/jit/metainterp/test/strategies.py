
import sys
from hypothesis import strategies
from rpython.jit.metainterp.resoperation import InputArgInt, ResOperation, rop
from rpython.jit.metainterp.history import ConstInt

machine_ints = strategies.integers(min_value=-sys.maxint - 1,
    max_value=sys.maxint)
intboxes = strategies.builds(InputArgInt)
intconsts = strategies.builds(ConstInt, machine_ints)
boxes = intboxes | intconsts
boxlists = strategies.lists(boxes, min_size=1).flatmap(
    lambda cis: strategies.lists(strategies.sampled_from(cis)))

@strategies.composite
def lists_of_operations(draw, inputboxes):
    def get(draw, l1, l2, index):
        if index < len(l1):
            return l1[index]
        index -= len(l1)
        if index >= len(l2):
            return draw(intconsts)
        return l2[index]

    size = draw(strategies.integers(min_value=1, max_value=100))
    inputargs = []
    for i in range(size):
        inputargs.append(draw(inputboxes))
    size = draw(strategies.integers(min_value=1, max_value=100))
    ops = []
    for i in range(size):
        s = strategies.integers(min_value=0, max_value=len(inputargs) + 2 * len(ops))
        arg0 = get(draw, inputargs, ops, draw(s))
        arg1 = get(draw, inputargs, ops, draw(s))
        ops.append(ResOperation(rop.INT_ADD, [arg0, arg1], -1))
    return ops

if __name__ == '__main__':
    import pprint
    pprint.pprint(lists_of_operations(intboxes).example())