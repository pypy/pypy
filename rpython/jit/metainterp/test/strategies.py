
import sys
from hypothesis import strategies
from rpython.jit.metainterp.resoperation import InputArgInt
from rpython.jit.metainterp.history import ConstInt

machine_ints = strategies.integers(min_value=-sys.maxint - 1,
    max_value=sys.maxint)
intboxes = strategies.builds(InputArgInt)
intconsts = strategies.builds(ConstInt, machine_ints)
boxes = intboxes | intconsts
boxlists = strategies.lists(boxes, min_size=1).flatmap(
    lambda cis: strategies.lists(strategies.sampled_from(cis)))