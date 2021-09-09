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


memoization = {}


@jit.elidable
def t_empty():
    return None


@jit.elidable
def t_is_empty(tstack):
    return tstack is None or tstack.pc == -100


@jit.elidable
def t_push(pc, next):
    key = pc, next
    if key in memoization:
        return memoization[key]
    result = TStack(pc, next)
    memoization[key] = result
    return result
