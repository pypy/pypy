'''Toy language for threaded code generation'''

import py
from rpython.jit.tl.tlopcode import *
from rpython.rlib.jit import (JitDriver, we_are_jitted, hint, dont_look_inside,
    loop_invariant, elidable, promote, jit_debug, assert_green,
    AssertGreenFailed, unroll_safe, current_trace_length, look_inside_iff,
    isconstant, isvirtual, set_param, record_exact_class, not_in_trace)


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


@elidable
def t_empty():
    return None


@elidable
def t_is_empty(tstack):
    return tstack is None or tstack.pc == -100


@elidable
def t_push(pc, next):
    key = pc, next
    if key in memoization:
        return memoization[key]
    result = TStack(pc, next)
    memoization[key] = result
    return result


@dont_look_inside
def emit_jump(*args):
    return args[0]


@dont_look_inside
def emit_ret(*args):
    return args[0]


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


def char2int(c):
    t = ord(c)
    if t & 128:
        t = -(-ord(c) & 0xff)
    return t


class W_Object:

    def getrepr(self):
        """
        Return an RPython string which represent the object
        """
        raise NotImplementedError

    def is_true(self):
        raise NotImplementedError

    def add(self, w_other):
        raise NotImplementedError

    def eq(self, w_other):
        raise NotImplementedError

    def lt(self, w_other):
        raise NotImplementedError

    def le(self, w_other):
        raise NotImplementedError

    def gt(self, w_other):
        raise NotImplementedError

    def ge(self, w_other):
        raise NotImplementedError


class W_IntObject(W_Object):

    def __init__(self, intvalue):
        self.intvalue = intvalue

    def getrepr(self):
        return str(self.intvalue)

    def is_true(self):
        return self.intvalue != 0

    def add(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue + w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def sub(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue - w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def mul(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue * w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def div(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue / w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError

    def eq(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue == w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def lt(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue < w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def le(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue <= w_other.intvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

class W_StringObject(W_Object):

    def __init__(self, strvalue):
        self.strvalue = strvalue

    def getrepr(self):
        return self.strvalue

    def is_true(self):
        return len(self.strvalue) != 0


class OperationError(Exception):
    pass


OPNAMES = []
HASARG = []

def define_op(name, has_arg=False):
    globals()[name] = len(OPNAMES)
    OPNAMES.append(name)
    HASARG.append(has_arg)

define_op("CONST_INT", True)
define_op("POP")
define_op("PUT")
define_op("PICK")
define_op("ADD")
define_op("SUB")
define_op("MUL")
define_op("DIV")
define_op("RETURN")
define_op("JUMP")
define_op("JUMP_IF", True)
define_op("CALL", True)
define_op("RET", True)
define_op("DUP")
define_op("NEWSTR", True)


def get_printable_location(pc, bytecode, entry_state, tstack):
    op = ord(bytecode[pc])
    name = OPNAMES[op]
    if HASARG[op]:
        arg = str(ord(bytecode[pc + 1]))
    else:
        arg = ''
    return "%s: %s %s" % (pc, name, arg)


jitdriver = JitDriver(greens=['pc', 'bytecode', 'entry_state', 'tstack'],
                      reds=['self'],
                      get_printable_location=get_printable_location,
                      threaded_code_gen=True)


class W_Frame:

    def __init__(self, bytecode):
        self.bytecode = bytecode
        self.size = 8
        self.stack = [None] * self.size
        self.sp = 0

        self.entry_state = None
        self.saved_stack = [None] * self.size
        self.saved_sp = 0

    @not_in_trace
    def save_state(self):
        W_Frame.saved_sp = self.sp
        for i in range(self.size):
            self.saved_stack[i] = self.stack[i]

    @not_in_trace
    def restore_state(self):
        for i in range(self.size):
            self.stack[i] = self.saved_stack[i]
        self.sp = self.saved_sp

    @dont_look_inside
    def push(self, w_x):
        self.stack[self.sp] = w_x
        self.sp += 1

    @dont_look_inside
    def pop(self):
        stackpos = self.sp - 1
        assert stackpos >= 0
        self.sp = stackpos
        res = self.stack[stackpos]
        self.stack[stackpos] = None
        return res

    @dont_look_inside
    def PUSH(self, pc):
        x = char2int(self.bytecode[pc])
        self.push(W_IntObject(x))

    @dont_look_inside
    def PICK(self, pc):
        w_x = self.stack(-1 - char2int(self.bytecode[pc]))
        self.push(w_x)

    @dont_look_inside
    def CONST_INT(self, x):
        if isinstance(x, int):
            self.push(W_IntObject(x))
        else:
            raise OperationError

    @dont_look_inside
    def ADD(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.add(w_y)
        self.push(w_z)

    @dont_look_inside
    def SUB(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.sub(w_y)
        self.push(w_z)

    @dont_look_inside
    def MUL(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mul(w_y)
        self.push(w_z)

    @dont_look_inside
    def DIV(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self.push(w_z)

    @dont_look_inside
    def DUP(self):
        w_x = self.pop()
        self.push(w_x)

    @dont_look_inside
    def LT(self):
        w_y = self.pop()
        w_x = self.pop()
        return w_x.lt(w_y)

    @dont_look_inside
    def NE(self):
        w_y = self.pop()
        w_x = self.pop()
        if w_x.eq(w_y).intvalue:
            self.push(W_IntObject(1))
        else:
            self.push(W_IntObject(0))

    @dont_look_inside
    def RETURN(self):
        return self.pop()

    @dont_look_inside
    def EQ(self):
        w_y = self.pop()
        w_x = self.pop()
        self.push(w_x.eq(w_y))

    def interp(self, w_x, pc=0,
               tstack=TStack(W_Object(), None)):
        entry_state = pc, tstack
        while pc < len(self.bytecode):
            jitdriver.jit_merge_point(pc=pc,
                                      bytecode=self.bytecode,
                                      entry_state=entry_state,
                                      self=self)
            opcode = ord(self.bytecode[pc])
            pc += 1

            if opcode == NOP:
                pass
            elif opcode == PUSH:
                self.PUSH(pc)
            elif opcode == ADD:
                self.ADD()
            elif opcode == SUB:
                self.SUB()
            elif opcode == MUL:
                self.MUL()
            elif opcode == DIV:
                self.DIV()
            elif opcode == RETURN:
                return self.RETURN()
            elif opcode == JUMP:
                t = int(bytecode[pc])
                if we_are_jitted():
                    if t_is_empty(tstack):
                        pc = t
                    else:
                        pc, tstack = tstack.t_pop()
                        pc = emit_jump(pc, t, None)
                else:
                    if t < pc:
                        entry_state = t, tstack
                        self.save_state()
                        jitdriver.can_enter_jit(pc=t, entry_state=entry_state,
                                                bytecode=self.bytecode, tstack=tstack,
                                                self=self)
                    pc = t


class TestW_Frame:

    def test_add(self):
        w_frame = W_Frame(None)
        w_x = W_IntObject(123)
        w_y = W_IntObject(456)
        w_frame.push(w_x)
        w_frame.push(w_y)
        w_frame.ADD()
        w_z = w_frame.pop()
        assert w_z.intvalue == 123 + 456

    def test_sub(self):
        w_frame = W_Frame(None)
        w_x = W_IntObject(123)
        w_y = W_IntObject(456)
        w_frame.push(w_x)
        w_frame.push(w_y)
        w_frame.SUB()
        w_z = w_frame.pop()
        assert w_z.intvalue == 123 - 456

    def test_mul(self):
        w_frame = W_Frame(None)
        w_x = W_IntObject(123)
        w_y = W_IntObject(456)
        w_frame.push(w_x)
        w_frame.push(w_y)
        w_frame.MUL()
        w_z = w_frame.pop()
        assert w_z.intvalue == 123 * 456

    def test_div(self):
        w_frame = W_Frame(None)
        w_x = W_IntObject(123)
        w_y = W_IntObject(456)
        w_frame.push(w_x)
        w_frame.push(w_y)
        w_frame.DIV()
        w_z = w_frame.pop()
        assert w_z.intvalue == 123 / 456
