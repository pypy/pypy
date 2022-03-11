from rpython.rlib import jit
from rpython.rlib.jit import JitDriver, we_are_jitted, we_are_translated, hint
from rpython.jit.tl.threadedcode.traverse_stack import *
from rpython.jit.tl.threadedcode.tlib import *

from rpython.jit.tl.threadedcode.object import *
from rpython.jit.tl.threadedcode.bytecode import *

def get_printable_location_tier1(pc, entry_state, bytecode, tstack):
    op = ord(bytecode[pc])
    name = bytecodes[op]
    if hasarg[op]:
        arg = str(ord(bytecode[pc + 1]))
    else:
        arg = ''
    return "%s: %s %s, tstack: %d" % (pc, name, arg, tstack.pc)

def get_printable_location(pc, bytecode):
    return get_printable_location_tier1(pc, 0, bytecode, t_empty())


tier1driver = JitDriver(
    greens=['pc', 'entry_state', 'bytecode', 'tstack'], reds=['self'],
    get_printable_location=get_printable_location_tier1, threaded_code_gen=True, is_recursive=True)


tjjitdriver = JitDriver(
    greens=['pc', 'bytecode',], reds=['self'],
    get_printable_location=get_printable_location, is_recursive=True)


class Frame(object):
    def __init__(self, bytecode, stack = [None] * 20480, stackpos = 0):
        self.bytecode = bytecode
        self.stack = stack
        self.stackpos = stackpos

    @jit.dont_look_inside
    def push(self, w_x):
        self.stack[self.stackpos] = w_x
        self.stackpos += 1

    @jit.dont_look_inside
    def pop(self):
        stackpos = self.stackpos - 1
        assert stackpos >= 0
        self.stackpos = stackpos
        res = self.stack[stackpos]
        self.stack[stackpos] = None
        return res

    @jit.dont_look_inside
    def take(self, n):
        assert len(self.stack) is not 0
        w_x = self.stack[self.stackpos - n - 1]
        assert w_x is not None
        return w_x

    @jit.dont_look_inside
    def drop(self, n):
        for _ in range(n):
            self.pop()

    @jit.dont_look_inside
    def rotate_two(self):
        w_1 = self.pop()
        w_2 = self.pop()
        self.push(w_2)
        self.push(w_1)

    @jit.dont_look_inside
    def rotate_three(self):
        w_1 = self.pop()
        w_2 = self.pop()
        w_3 = self.pop()
        self.push(w_1)
        self.push(w_2)
        self.push(w_3)

    @jit.not_rpython
    def dump(self):
        out = ""
        for i in range(self.stackpos):
            w_x = self.stack[i]
            if isinstance(w_x, W_Object):
                out = "%s, %s" % (w_x.getrepr(), out)
        out = "[" + out + "]"
        print "stackpos:", str(self.stackpos), out

    @jit.dont_look_inside
    def is_true(self, dummy):
        if dummy:
            return self.take(0).is_true()
        w_x = self.pop()
        res = w_x.is_true()
        return res

    @jit.dont_look_inside
    def CONST_INT(self, pc, dummy):
        if dummy:
            return
        if isinstance(pc, int):
            x = ord(self.bytecode[pc])
            self.push(W_IntObject(x))
        else:
            raise OperationError

    @jit.dont_look_inside
    def CONST_FLOAT(self, pc, dummy):
        if dummy:
            return
        if isinstance(pc, float):
            x = ord(self.bytecode[pc])
            self.push(W_FloatObject(x))
        else:
            raise OperationError

    @jit.dont_look_inside
    def PUSH(self, w_x, dummy):
        if dummy:
            return
        self.push(w_x)

    @jit.dont_look_inside
    def POP(self, dummy):
        if dummy:
            return self.take(0)
        return self.pop()

    @jit.dont_look_inside
    def DROP(self, n, dummy):
        if dummy:
            return
        for _ in range(n):
            self.pop()

    @jit.dont_look_inside
    def POP1(self, dummy):
        if dummy:
            return
        v = self.pop()
        _ = self.pop()
        self.push(v)

    @jit.dont_look_inside
    def ADD(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.add(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def SUB(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.sub(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MUL(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mul(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DIV(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MOD(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mod(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DUP(self, dummy):
        if dummy:
            return
        w_x = self.pop()
        self.push(w_x)
        self.push(w_x)

    @jit.dont_look_inside
    def DUPN(self, pc, dummy):
        if dummy:
            return
        n = ord(self.bytecode[pc])
        w_x = self.take(n)
        self.push(w_x)

    @jit.dont_look_inside
    def LT(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.lt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def GT(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.gt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def EQ(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        self.push(w_x.eq(w_y))

    @jit.dont_look_inside
    def NE(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        if w_x.eq(w_y).intvalue:
            self.push(W_IntObject(1))
        else:
            self.push(W_IntObject(0))

    @jit.dont_look_inside
    def CALL(self, oldframe, t, argnum, dummy):
        if dummy:
            return
        w_x = self.interp(t)
        oldframe.drop(argnum)
        if w_x:
            oldframe.push(w_x)

    @jit.dont_look_inside
    def RET(self, n, dummy):
        if dummy:
            return
        v = self.pop()
        return v

    @jit.dont_look_inside
    def PRINT(self, dummy):
        if dummy:
            return
        v = self.take(0)
        print v.getrepr()

    @jit.dont_look_inside
    def FRAME_RESET(self, o, l, n, dummy):
        if dummy:
            return

        ret = self.stack[self.stackpos - n - l - 1]
        old_base = self.stackpos - n - l - o - 1
        new_base = self.stackpos - n
        i = 0
        while i != n:
            self.stack[old_base + i] = self.stack[new_base + i]
            i += 1
        self.stackpos = old_base + n + 1

    def interp(self, pc=0, dummy=False):
        tstack = t_empty()
        entry_state = pc
        bytecode = self.bytecode

        if dummy:
            return

        while pc < len(bytecode):
            tier1driver.jit_merge_point(bytecode=bytecode, entry_state=entry_state,
                                        pc=pc, tstack=tstack, self=self)

            # print get_printable_location_tier1(pc, entry_state, bytecode, tstack)
            # self.dump()

            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                if we_are_jitted():
                    self.CONST_INT(pc, dummy=True)
                else:
                    self.CONST_INT(pc, dummy=False)
                pc += 1

            elif opcode == POP:
                if we_are_jitted():
                    self.POP(dummy=True)
                else:
                    self.POP(dummy=False)

            elif opcode == POP1:
                if we_are_jitted():
                    self.POP1(dummy=True)
                else:
                    self.POP1(dummy=False)

            elif opcode == DUP:
                if we_are_jitted():
                    self.DUP(dummy=True)
                else:
                    self.DUP(dummy=False)

            elif opcode == DUPN:
                if we_are_jitted():
                    self.DUPN(pc, dummy=True)
                else:
                    self.DUPN(pc, dummy=False)
                pc += 1

            elif opcode == LT:
                if we_are_jitted():
                    self.LT(dummy=True)
                else:
                    self.LT(dummy=False)

            elif opcode == GT:
                if we_are_jitted():
                    self.GT(dummy=True)
                else:
                    self.GT(dummy=False)

            elif opcode == EQ:
                if we_are_jitted():
                    self.EQ(dummy=True)
                else:
                    self.EQ(dummy=False)

            elif opcode == ADD:
                if we_are_jitted():
                    self.ADD(dummy=True)
                else:
                    self.ADD(dummy=False)

            elif opcode == SUB:
                if we_are_jitted():
                    self.SUB(dummy=True)
                else:
                    self.SUB(dummy=False)

            elif opcode == DIV:
                if we_are_jitted():
                    self.DIV(dummy=True)
                else:
                    self.DIV(dummy=False)

            elif opcode == MUL:
                if we_are_jitted():
                    self.MUL(dummy=True)
                else:
                    self.MUL(dummy=False)

            elif opcode == MOD:
                if we_are_jitted():
                    self.MOD(dummy=True)
                else:
                    self.MOD(dummy=False)

            elif opcode == CALL:
                t = ord(bytecode[pc])
                argnum = ord(bytecode[pc + 1])
                pc += 2

                # create a new frame
                frame = Frame(bytecode)
                i = self.stackpos - argnum - 1
                assert i >= 0
                frame.stack = self.stack[i:]
                frame.stackpos = argnum + 1

                if we_are_jitted():
                    frame.CALL(self, t, argnum, dummy=True)
                else:
                    entry_state = t
                    tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                              pc=t, tstack=tstack, self=frame)
                    frame.CALL(self, t, argnum, dummy=False)

            elif opcode == RET:
                argnum = hint(ord(bytecode[pc]), promote=True)
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.RET(argnum, dummy=True)
                        pc = entry_state
                        pc = emit_ret(pc, w_x)
                        tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=pc, tstack=tstack, self=self)
                    else:
                        w_x = self.RET(argnum, dummy=True)
                        pc, tstack = tstack.t_pop()
                        pc = emit_ret(pc, w_x)
                else:
                    return self.RET(argnum, dummy=False)

            elif opcode == JUMP:
                t = ord(bytecode[pc])
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        if t < pc:
                            tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                      pc=t, tstack=tstack, self=self)
                        pc = t

                    else:
                        pc, tstack = tstack.t_pop()
                    if t < pc:
                        pc = emit_jump(pc, t)
                else:
                    if t < pc:
                        entry_state = t
                        tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=t, tstack=tstack, self=self)
                    pc = t

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                if we_are_jitted():
                    if self.is_true(dummy=True):
                        tstack = t_push(pc, tstack)
                        pc = target
                    else:
                        tstack = t_push(target, tstack)
                else:
                    if self.is_true(dummy=False):
                        if target < pc:
                            entry_state = target
                            tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                      pc=target, tstack=tstack, self=self)
                        pc = target

            elif opcode == EXIT:
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.POP(dummy=True)
                        pc = entry_state
                        pc = emit_ret(pc, w_x)
                        tier1driver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=pc, tstack=tstack, self=self)
                    else:
                        w_x = self.POP(dummy=True)
                        pc, tstack = tstack.t_pop()
                        pc = emit_ret(pc, w_x)
                else:
                    return self.POP(dummy=False)

            elif opcode == PRINT:
                if we_are_jitted():
                    self.PRINT(dummy=True)
                else:
                    self.PRINT(dummy=True)

            elif opcode == FRAME_RESET:
                raise NotImplementedError

            elif opcode == NOP:
                continue

            else:
                assert False, 'Unknown opcode: %s' % bytecodes[opcode]


def run(bytecode, w_arg, entry=None):
    frame = Frame(bytecode)
    frame.push(w_arg); frame.push(w_arg)
    w_result = frame.interp()
    # frame.dump()
    return w_result
