from rpython.rlib.objectmodel import newlist_hint

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
        items[self.index] = w_item
        self.index += 1
