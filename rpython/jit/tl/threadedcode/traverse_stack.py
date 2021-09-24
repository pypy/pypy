from rpython.rlib import jit

class TStack:
    _immutable_fields_ = ['pc', 'next']

    def __init__(self, pc, next):
        self.pc = pc
        self.next = next

    def __repr__(self):
        return "TStack(%d, %s)" % (self.pc, repr(self.next))

    def t_pop(self):
        return self.pc, self.next

    @jit.elidable
    def t_is_empty(self):
        return self is _T_EMPTY

_T_EMPTY = TStack(-42, None)

memoization = {}


@jit.elidable
def t_empty():
    return _T_EMPTY


@jit.elidable
def t_push(pc, next):
    key = pc, next
    if key in memoization:
        return memoization[key]
    result = TStack(pc, next)
    memoization[key] = result
    return result
