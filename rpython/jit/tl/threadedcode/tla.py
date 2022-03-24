from rpython.rlib import jit
from rpython.rlib.jit import JitDriver, we_are_jitted, we_are_translated, hint
from rpython.jit.tl.threadedcode.traverse_stack import *
from rpython.jit.tl.threadedcode.tlib import *

from rpython.jit.tl.threadedcode.object import *
from rpython.jit.tl.threadedcode.bytecode import *

def get_printable_location_tier1(pc, call_entry, bytecode, tstack):
    op = ord(bytecode[pc])
    name = bytecodes[op]
    if hasarg[op]:
        arg = str(ord(bytecode[pc + 1]))
    else:
        arg = ''
    return "%s: %s %s, tstack: %d" % (pc, name, arg, tstack.pc)

def get_printable_location(pc, bytecode):
    op = ord(bytecode[pc])
    name = bytecodes[op]
    if hasarg[op]:
        arg = str(ord(bytecode[pc + 1]))
    else:
        arg = ''
    return "%s: %s %s" % (pc, name, arg)


tier1driver = JitDriver(
    greens=['pc', 'call_entry', 'bytecode', 'tstack'], reds=['self'],
    get_printable_location=get_printable_location_tier1,
    threaded_code_gen=True)


tier2driver = JitDriver(
    greens=['pc', 'bytecode',], reds=['self'],
    get_printable_location=get_printable_location, is_recursive=True)


class Frame(object):
    def __init__(self, bytecode, stack=[None] * 128, stackpos=0):
        self.bytecode = bytecode
        self.stack = stack
        self.stackpos = stackpos

    @jit.unroll_safe
    def copy_frame(self, argnum, dummy=False):

        oldstack = self.stack
        oldstackpos = self.stackpos
        framepos = oldstackpos - argnum - 1
        assert framepos >= 0

        newstack = [None] * len(self.stack)
        for i in range(framepos, oldstackpos):
            # j = oldstackpos - i - 1
            newstack[i - framepos] = oldstack[i]

        newstack[argnum + 1] = oldstack[oldstackpos - 1]
        return Frame(self.bytecode, newstack, argnum + 2)

    @jit.dont_look_inside
    def push(self, w_x):
        self.stack[self.stackpos] = w_x
        self.stackpos += 1

    def _push(self, w_x):
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

    def _pop(self):
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

    def _take(self, n):
        assert len(self.stack) is not 0
        w_x = self.stack[self.stackpos - n - 1]
        assert w_x is not None
        return w_x

    @jit.dont_look_inside
    def drop(self, n):
        for _ in range(n):
            self.pop()

    @jit.unroll_safe
    def _drop(self, n):
        for _ in range(n):
            self._pop()

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
                out = "%s, %s" % (out, w_x.getrepr())
        out = "[" + out + "]"
        print "stackpos: %d %s" % (self.stackpos, out)

    @jit.dont_look_inside
    def is_true(self, dummy):
        if dummy:
            return self.take(0).is_true()
        w_x = self.pop()
        return w_x.is_true()

    def _is_true(self):
        w_x = self._pop()
        return w_x.is_true()

    @jit.dont_look_inside
    def CONST_INT(self, pc, dummy):
        if dummy:
            return
        if isinstance(pc, int):
            x = ord(self.bytecode[pc])
            self.push(W_IntObject(x))
        else:
            raise OperationError

    def _CONST_INT(self, pc):
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

    def _CONST_FLOAT(self, pc):
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

    def _PUSH(self, w_x):
        self.push(w_x)

    @jit.dont_look_inside
    def POP(self, dummy):
        if dummy:
            return self.take(0)
        return self.pop()

    def _POP(self):
        return self.pop()

    @jit.dont_look_inside
    def DROP(self, n, dummy):
        if dummy:
            return
        for _ in range(n):
            self.pop()

    @jit.unroll_safe
    def _DROP(self, n):
        for _ in range(n):
            self._pop()

    @jit.dont_look_inside
    def POP1(self, dummy):
        if dummy:
            return
        v = self.pop()
        _ = self.pop()
        self.push(v)

    def _POP1(self):
        v = self._pop()
        _ = self._pop()
        self._push(v)

    @jit.dont_look_inside
    def ADD(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.add(w_y)
        self.push(w_z)

    def _ADD(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.add(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def SUB(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.sub(w_y)
        self.push(w_z)

    def _SUB(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.sub(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def MUL(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mul(w_y)
        self.push(w_z)

    def _MUL(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.mul(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def DIV(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self.push(w_z)

    def _DIV(self):
        w_y = self._pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def MOD(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mod(w_y)
        self.push(w_z)

    def _MOD(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.mod(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def DUP(self, dummy):
        if dummy:
            return
        w_x = self.pop()
        self.push(w_x)
        self.push(w_x)

    def _DUP(self):
        w_x = self._pop()
        self._push(w_x)
        self._push(w_x)

    @jit.dont_look_inside
    def DUPN(self, pc, dummy):
        if dummy:
            return
        n = ord(self.bytecode[pc])
        w_x = self.take(n)
        self.push(w_x)

    def _DUPN(self, pc):
        n = ord(self.bytecode[pc])
        w_x = self._take(n)
        self._push(w_x)

    @jit.dont_look_inside
    def LT(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.lt(w_y)
        self.push(w_z)

    def _LT(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.lt(w_y)
        self._push(w_z)

    @jit.dont_look_inside
    def GT(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.gt(w_y)
        self.push(w_z)

    def _GT(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.gt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def EQ(self, dummy):
        if dummy:
            return
        w_y = self.pop()
        w_x = self.pop()
        self.push(w_x.eq(w_y))

    def _EQ(self):
        w_y = self._pop()
        w_x = self._pop()
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

    def _NE(self):
        w_y = self._pop()
        w_x = self._pop()
        if w_x.eq(w_y).intvalue:
            self._push(W_IntObject(1))
        else:
            self._push(W_IntObject(0))

    @jit.dont_look_inside
    def CALL(self, oldframe, t, argnum, dummy):
        if dummy:
            return
        w_x = self.interp(t)
        oldframe.drop(argnum)
        if w_x:
            oldframe.push(w_x)

    def CALL_ASSEMBLER(self, oldframe, t, argnum, bytecode, tstack, dummy):
        "Special handler to be compiled to call_assembler_r"
        w_x = self.interp_CALL_ASSEMBLER(t, t, bytecode, tstack, dummy)
        oldframe.DROP(argnum, dummy)
        if w_x:
            oldframe.PUSH(w_x, dummy)

    def _CALL(self, oldframe, t, argnum):
        w_x = self._interp(t)
        oldframe._drop(argnum)
        if w_x:
            oldframe._push(w_x)

    @jit.dont_look_inside
    def RET(self, n, dummy):
        if dummy:
            return
        v = self.pop()
        return v

    def _RET(self, n):
        v = self._pop()
        return v

    @jit.dont_look_inside
    def PRINT(self, dummy):
        if dummy:
            return
        v = self.take(0)
        print v.getrepr()

    def _PRINT(self):
        v = self._take(0)
        # print v.getrepr()

    @jit.dont_look_inside
    def FRAME_RESET(self, o, l, n, dummy):
        if dummy:
            return

        ret = self.stack[self.stackpos - n - 1]
        old_base = self.stackpos - n
        new_base = self.stackpos - o - n - l - 1

        for i in range(n):
            self.stack[new_base + i] = self.stack[old_base + i]
            self.stack[old_base + i] = None

        self.stack[new_base + n] = ret
        self.stackpos = new_base + n + 1

    @jit.unroll_safe
    def _FRAME_RESET(self, o, l, n):
        ret = self.stack[self.stackpos - n - 1]
        old_base = self.stackpos - n
        new_base = self.stackpos - o - n - l - 1

        for i in range(n):
            self.stack[new_base + i] = self.stack[old_base + i]
            self.stack[old_base + i] = None

        self.stack[new_base + n] = ret
        self.stackpos = new_base + n + 1

    def _interp(self, pc=0):
        bytecode = self.bytecode

        while pc < len(bytecode):
            tier2driver.jit_merge_point(bytecode=bytecode, pc=pc, self=self)

            # print get_printable_location(pc, bytecode)

            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self._CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self._POP()

            elif opcode == POP1:
                self._POP1()

            elif opcode == DUP:
                self._DUP()

            elif opcode == DUPN:
                self._DUPN(pc)
                pc += 1

            elif opcode == LT:
                self._LT()

            elif opcode == GT:
                self._GT()

            elif opcode == EQ:
                self._EQ()

            elif opcode == ADD:
                self._ADD()

            elif opcode == SUB:
                self._SUB()

            elif opcode == DIV:
                self._DIV()

            elif opcode == MUL:
                self._MUL()

            elif opcode == MOD:
                self._MOD()

            elif opcode == CALL:
                t = ord(bytecode[pc])
                argnum = ord(bytecode[pc + 1])
                pc += 2

                # create a new frame
                frame = self.copy_frame(argnum)
                # tier2driver.can_enter_jit(bytecode=bytecode, pc=t, self=frame)
                frame._CALL(self, t, argnum)

            elif opcode == RET:
                argnum = hint(ord(bytecode[pc]), promote=True)
                pc += 1
                return self._RET(argnum,)

            elif opcode == JUMP:
                t = ord(bytecode[pc])
                pc += 1
                if t < pc:
                    tier2driver.can_enter_jit(bytecode=bytecode, pc=t, self=self)

                pc = t

            elif opcode == JUMP_IF:
                t = ord(bytecode[pc])
                pc += 1
                if self._is_true():
                    if t < pc:
                        tier2driver.can_enter_jit(bytecode=bytecode, pc=t, self=self)
                    pc = t

            elif opcode == EXIT:
                return self._POP()

            elif opcode == PRINT:
                self._PRINT()

            elif opcode == FRAME_RESET:
                old_arity = ord(bytecode[pc])
                local_size = ord(bytecode[pc+1])
                new_arity = ord(bytecode[pc+2])
                pc += 3
                self._FRAME_RESET(old_arity, local_size, new_arity)

            elif opcode == NOP:
                continue

            else:
                assert False, 'Unknown opcode: %s' % bytecodes[opcode]

    @jit.dont_look_inside
    def interp_CALL_ASSEMBLER(self, pc, call_entry, bytecode, tstack, dummy):
        if dummy:
            return self.take(0)
        return self.interp(pc, dummy)

    def interp(self, pc=0, dummy=False):
        if dummy:
            return

        tstack = t_empty()
        call_entry = pc
        bytecode = self.bytecode

        while pc < len(bytecode):
            tier1driver.jit_merge_point(bytecode=bytecode, call_entry=call_entry,
                                        pc=pc, tstack=tstack, self=self)

            # print get_printable_location_tier1(pc, call_entry, bytecode, tstack)
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
                frame = self.copy_frame(argnum)

                if we_are_jitted():
                    frame.CALL(self, t, argnum, dummy=True)
                    # frame.CALL_ASSEMBLER(self, t, argnum, bytecode, tstack, dummy=True)
                else:
                    call_entry = t
                    tier1driver.can_enter_jit(bytecode=bytecode, call_entry=t,
                                              pc=t, tstack=tstack, self=frame)
                    frame.CALL(self, t, argnum, dummy=False)
                    # frame.CALL_ASSEMBLER(self, t, argnum, bytecode, tstack, dummy=False)

            elif opcode == RET:
                argnum = hint(ord(bytecode[pc]), promote=True)
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.RET(argnum, dummy=True)
                        pc = call_entry
                        pc = emit_ret(pc, w_x)
                        tier1driver.can_enter_jit(bytecode=bytecode,
                                                  call_entry=call_entry,
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
                            tier1driver.can_enter_jit(bytecode=bytecode,
                                                      call_entry=call_entry,
                                                      pc=t, tstack=tstack, self=self)
                        pc = t

                    else:
                        pc, tstack = tstack.t_pop()
                    if t < pc:
                        pc = emit_jump(pc, t)
                else:
                    if t < pc:
                        tier1driver.can_enter_jit(bytecode=bytecode,
                                                  call_entry=call_entry,
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
                            call_entry = target
                            tier1driver.can_enter_jit(bytecode=bytecode,
                                                      call_entry=call_entry,
                                                      pc=target, tstack=tstack, self=self)
                        pc = target

            elif opcode == EXIT:
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.POP(dummy=True)
                        pc = call_entry
                        pc = emit_ret(pc, w_x)
                        tier1driver.can_enter_jit(bytecode=bytecode,
                                                  call_entry=call_entry,
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
                old_arity = ord(bytecode[pc])
                local_size = ord(bytecode[pc+1])
                new_arity = ord(bytecode[pc+2])
                pc += 3
                if we_are_jitted():
                    self.FRAME_RESET(old_arity, local_size, new_arity, dummy=True)
                else:
                    self.FRAME_RESET(old_arity, local_size, new_arity, dummy=False)

            elif opcode == NOP:
                continue

            else:
                assert False, 'Unknown opcode: %s' % bytecodes[opcode]


def run(bytecode, w_arg, entry=None, debug=False):
    frame = Frame(bytecode)
    frame.push(w_arg); frame.push(w_arg)
    if entry == "tracing":
        w_result = frame._interp()
    else:
        w_result = frame.interp()
    # frame.dump()
    return w_result
