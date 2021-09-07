from rpython.rlib.jit import (JitDriver, we_are_jitted, hint, dont_look_inside,
    loop_invariant, elidable, promote, jit_debug, assert_green,
    AssertGreenFailed, unroll_safe, current_trace_length, look_inside_iff,
    isconstant, isvirtual, set_param, record_exact_class, not_in_trace)

class Frame(object):
    size = 10

    def __init__(self, bytecode):
        self.stack = [0] * Frame.size
        self.sp = 0
        self.bytecode = bytecode

    @dont_look_inside
    def push(self, v):
        self.stack[self.sp] = v
        self.sp += 1

    @dont_look_inside
    def pop(self):
        self.sp -= 1
        return self.stack[self.sp]

    def copy(self):
        l = [0] * len(self.stack)
        x = self.sp
        for i in range(len(self.stack)):
            l[i] = self.stack[i]
        return  l, x

    @dont_look_inside
    def const_int(self, v):
        self.push(v)

    @dont_look_inside
    def dup(self):
        v = self.pop()
        self.push(v)
        self.push(v)

    @dont_look_inside
    def add(self):
        y = self.pop()
        x = self.pop()
        z = x + y
        self.push(z)

    @dont_look_inside
    def sub(self):
        y = self.pop()
        x = self.pop()
        z = x - y
        self.push(z)

    @dont_look_inside
    def lt(self):
        y = self.pop()
        x = self.pop()
        if x < y:
            self.push(0)
        else:
            self.push(1)

    @dont_look_inside
    def is_true(self):
        return self.pop() != 0
