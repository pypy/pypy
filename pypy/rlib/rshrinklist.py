
class AbstractShrinkList(object):
    _mixin_ = True

    def __init__(self):
        self._list = []
        self._next_shrink = 16

    def append(self, x):
        self._do_shrink()
        self._list.append(x)

    def items(self):
        return self._list

    def _do_shrink(self):
        if len(self._list) >= self._next_shrink:
            rest = 0
            for x in self._list:
                if self.must_keep(x):
                    self._list[rest] = x
                    rest += 1
            del self._list[rest:]
            self._next_shrink = 16 + 2 * rest

    def must_keep(self, x):
        raise NotImplementedError
