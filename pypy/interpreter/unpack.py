from rpython.rlib.objectmodel import newlist_hint
from rpython.rlib import jit

from pypy.interpreter.error import OperationError

class UnpackTarget(object):
    def __init__(self, space):
        self.space = space

    def append(self, w_obj):
        raise NotImplementedError("abstract base class")


class InterpListUnpackTarget(UnpackTarget):
    def __init__(self, space, w_iterable):
        self.space = space
        try:
            items_w = newlist_hint(self.space.length_hint(w_iterable, 0))
        except MemoryError:
            items_w = [] # it might have lied
        self.items_w = items_w

    def append(self, w_obj):
        self.items_w.append(w_obj)


class FixedSizeUnpackTarget(UnpackTarget):
    def __init__(self, space, expected_size):
        self.items_w = [None] * expected_size
        self.index = 0

    def append(self, w_obj):
        if self.index == len(self.items_w):
            raise OperationError(self.w_ValueError,
                                self.wrap("too many values to unpack"))
        self.items_w[self.index] = w_item
        self.index += 1



unpack_into_driver = jit.JitDriver(name='unpack_into',
                                   greens=['unroll', 'w_type'],
                                   reds=['unpack_target', 'w_iterator'])

def generic_unpack_into(w_iterable, space, unpack_target, unroll=False):
    w_iterator = space.iter(w_iterable)
    w_type = space.type(w_iterator)
    while True:
        if not unroll:
            unpack_into_driver.can_enter_jit(w_type=w_type, unroll=unroll,
                                             w_iterator=w_iterator,
                                             unpack_target=unpack_target)
        unpack_into_driver.jit_merge_point(w_type=w_type, unroll=unroll,
                                           w_iterator=w_iterator,
                                           unpack_target=unpack_target)
        try:
            w_item = space.next(w_iterator)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break  # done
        unpack_target.append(w_item)

