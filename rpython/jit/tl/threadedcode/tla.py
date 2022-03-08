from rpython.rlib import jit
from rpython.rlib.jit import JitDriver, we_are_jitted, we_are_translated, hint
from rpython.jit.tl.threadedcode.traverse_stack import *
from rpython.jit.tl.threadedcode.tlib import *

from rpython.jit.tl.threadedcode.object import *
from rpython.jit.tl.threadedcode.bytecode import *

def get_printable_location_tier1(pc, entry_pc, bytecode, tstack):
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
    greens=['pc', 'entry_pc', 'bytecode', 'tstack'], reds=['self'],
    get_printable_location=get_printable_location_tier1, threaded_code_gen=True,
    is_recursive=True)


tjjitdriver = JitDriver(
    greens=['pc', 'bytecode',], reds=['self'],
    get_printable_location=get_printable_location, is_recursive=True)


class Frame(object):
    def __init__(self, bytecode):
        self.bytecode = bytecode
        self.stack = [None] * 10240
        self.stackpos = 0

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
        return self.stack[self.stackpos - n - 1]

    @jit.dont_look_inside
    def drop(self, n):
        for _ in range(n):
            self.pop()

    @jit.not_in_trace
    def dump(self):
        out = ""
        for elem in self.stack:
            if elem is None:
                break
            if isinstance(elem, W_Object):
                out = "%s, %s" % (elem.getrepr(), out)
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
    def CALL(self, t, dummy):
        if dummy:
            return
        res = self.interp(t)
        if res:
            self.push(res)

    @jit.dont_look_inside
    def CALL_NORMAL(self, t):
        res = self.interp_normal(t)
        if res:
            self.push(res)

    @jit.dont_look_inside
    def CALL_JIT(self, t):
        res = self.interp_jit(t)
        if res:
            self.push(res)

    @jit.dont_look_inside
    def RET(self, n, dummy):
        if dummy:
            return
        v = self.pop()
        self.drop(n)
        return v

    @jit.dont_look_inside
    def PRINT(self, dummy):
        if dummy:
            return
        v = self.take(0)
        print v.getrepr()

    def _push(self, w_x):
        self.stack[self.stackpos] = w_x
        self.stackpos += 1

    def _pop(self):
        stackpos = self.stackpos - 1
        assert stackpos >= 0
        self.stackpos = stackpos
        res = self.stack[stackpos]
        self.stack[stackpos] = None
        return res

    def _take(self,n):
        assert len(self.stack) is not 0
        return self.stack[self.stackpos - n - 1]

    def _drop(self, n):
        for _ in range(n):
            self.pop()

    def _is_true(self):
        w_x = self.pop()
        res = w_x.is_true()
        return res

    def _CONST_INT(self, pc):
        if isinstance(pc, int):
            x = ord(self.bytecode[pc])
            self._push(W_IntObject(x))
        else:
            raise OperationError

    def _CONST_FLOAT(self, pc):
        if isinstance(pc, float):
            x = ord(self.bytecode[pc])
            self._push(W_FloatObject(x))
        else:
            raise OperationError

    def _POP1(self):
        v = self._pop()
        _ = self._pop()
        self._push(v)

    def _ADD(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.add(w_y)
        self._push(w_z)

    def _SUB(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.sub(w_y)
        self._push(w_z)

    def _MUL(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.mul(w_y)
        self._push(w_z)

    def _DIV(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.div(w_y)
        self._push(w_z)

    def _MOD(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.mod(w_y)
        self._push(w_z)

    def _DUP(self):
        w_x = self._pop()
        self._push(w_x)
        self._push(w_x)

    def _DUPN(self, pc):
        n = ord(self.bytecode[pc])
        w_x = self._take(n)
        self._push(w_x)
        self._push(w_x)

    def _LT(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.lt(w_y)
        self._push(w_z)

    def _GT(self):
        w_y = self._pop()
        w_x = self._pop()
        w_z = w_x.gt(w_y)
        self._push(w_z)

    def _EQ(self):
        w_y = self._pop()
        w_x = self._pop()
        self._push(w_x.eq(w_y))

    def _NE(self):
        w_y = self._pop()
        w_x = self._pop()
        if w_x.eq(w_y).intvalue:
            self.push(W_IntObject(1))
        else:
            self.push(W_IntObject(0))

    def _CALL(self, t):
        res = self.interp(t)
        if res:
            self.push(res)

    def _CALL_NORMAL(self, t):
        res = self.interp_normal(t)
        if res is not None:
            self._push(res)

    def _CALL_JIT(self, t):
        res = self.interp_jit(t)
        if res is not None:
            self._push(res)

    def _RET(self, n):
        v = self._pop()
        self._drop(n)
        return v

    def _PRINT(self):
        v = self._take(0)
        print v.getrepr()

    def interp_jit(self, pc=0):
        bytecode = self.bytecode
        while pc < len(bytecode):
            tjjitdriver.jit_merge_point(pc=pc, bytecode=bytecode, self=self)

            # print get_printable_location(pc, bytecode)
            # self.dump()
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self._CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self._pop()

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
                pc += 1
                self._CALL(t)

            elif opcode == CALL_NORMAL:
                t = ord(bytecode[pc])
                pc += 1
                self._CALL_NORMAL(t)

            elif opcode == CALL_JIT:
                t = ord(bytecode[pc])
                pc += 1
                self._CALL_JIT(t)

            elif opcode == RET:
                argnum = ord(bytecode[pc])
                pc += 1
                return self._RET(argnum)

            elif opcode == JUMP:
                target = ord(bytecode[pc])
                if target < pc:
                    tjjitdriver.can_enter_jit(pc=target, bytecode=bytecode, self=self)
                pc = target

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                if self._is_true():
                    if target < pc:
                        tjjitdriver.can_enter_jit(pc=target, bytecode=bytecode, self=self)
                    pc = target

            elif opcode == EXIT:
                return self._pop()

            elif opcode == PRINT:
                self._PRINT()

            else:
                assert False, 'Unknown opcode: %d' % opcode

    def interp_normal(self, pc=0):
        bytecode = self.bytecode

        while pc < len(bytecode):
            # print get_printable_location_tc(pc, entry_pc, bytecode, tstack)
            # self.dump()
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self.CONST_INT(pc, dummy=False)
                pc += 1

            elif opcode == POP:
                self.POP(dummy=False)

            elif opcode == POP1:
                self.POP1(dummy=False)

            elif opcode == DUP:
                self.DUP(dummy=False)

            elif opcode == DUPN:
                self.DUPN(pc, dummy=False)
                pc += 1

            elif opcode == LT:
                self.LT(dummy=False)

            elif opcode == GT:
                self.GT(dummy=False)

            elif opcode == EQ:
                self.EQ(dummy=False)

            elif opcode == ADD:
                self.ADD(dummy=False)

            elif opcode == SUB:
                self.SUB(dummy=False)

            elif opcode == DIV:
                self.DIV(dummy=False)

            elif opcode == MUL:
                self.MUL(dummy=False)

            elif opcode == MOD:
                self.MOD(dummy=False)

            elif opcode == CALL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_NORMAL(t)

            elif opcode == RET:
                argnum = ord(bytecode[pc])
                pc += 1
                return self.RET(argnum, dummy=False)

            elif opcode == JUMP:
                target = ord(bytecode[pc])
                pc = target

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                if self.is_true(dummy=False):
                    pc = target

            elif opcode == EXIT:
                return self.POP(dummy=False)

            elif opcode == PRINT:
                self.PRINT(dummy=False)

            else:
                assert False, 'Unknown opcode: %d' % opcode

    def interp(self, pc=0, dummy=False):
        tstack = t_empty()
        entry_pc = pc
        bytecode = self.bytecode

        if dummy:
            return

        while pc < len(bytecode):
            tier1driver.jit_merge_point(bytecode=bytecode, entry_pc=entry_pc,
                                        pc=pc, tstack=tstack, self=self)

            # print get_printable_location_tier1(pc, entry_pc, bytecode, tstack)
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
                pc += 1
                if we_are_jitted():
                    self.CALL(t, dummy=False)
                else:
                    entry_pc = t; # self.save_state()
                    tier1driver.can_enter_jit(bytecode=bytecode, entry_pc=entry_pc,
                                              pc=t, tstack=tstack, self=self)
                    self.CALL(t, dummy=False)

            elif opcode == CALL_NORMAL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_NORMAL(t)

            elif opcode == CALL_JIT:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_JIT(t)

            elif opcode == RET:
                argnum = hint(ord(bytecode[pc]), promote=True)
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.RET(argnum, dummy=True)
                        pc = entry_pc
                        pc = emit_ret(pc, w_x)
                        tier1driver.can_enter_jit(bytecode=bytecode, entry_pc=entry_pc,
                                                  pc=pc, tstack=tstack, self=self)
                    else:
                        w_x = self.RET(argnum, dummy=True)
                        pc, tstack = tstack.t_pop()
                        pc = emit_ret(pc, w_x)
                else:
                    w_x = self.RET(argnum, dummy=False)
                    return w_x

            elif opcode == JUMP:
                t = ord(bytecode[pc])
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        if t < pc:
                            tier1driver.can_enter_jit(bytecode=bytecode, entry_pc=entry_pc,
                                                      pc=t, tstack=tstack, self=self)
                        pc = t

                    else:
                        pc, tstack = tstack.t_pop()
                    if t < pc:
                        pc = emit_jump(pc, t)
                else:
                    if t < pc:
                        entry_pc = t; # self.save_state()
                        tier1driver.can_enter_jit(bytecode=bytecode, entry_pc=entry_pc,
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
                            entry_pc = target; # self.save_state()
                            tier1driver.can_enter_jit(bytecode=bytecode, entry_pc=entry_pc,
                                                      pc=target, tstack=tstack, self=self)
                        pc = target

            elif opcode == EXIT:
                if we_are_jitted():
                    w_x = self.POP(dummy=True)
                    if tstack.t_is_empty():
                        return w_x
                    else:
                        pc, tstack = tstack.t_pop()
                        pc = emit_ret(pc, w_x)
                else:
                    return self.POP(dummy=False)

            elif opcode == PRINT:
                if we_are_jitted():
                    self.PRINT(dummy=True)
                else:
                    self.PRINT(dummy=False)

            else:
                assert False, 'Unknown opcode: %s' % bytecodes[opcode]


def run(bytecode, w_arg, entry=None):
    frame = Frame(bytecode)
    frame.push(w_arg)
    if entry == "tracing" or entry == "tr":
        w_result = frame.interp_jit()
    else:
        w_result = frame.interp()
    frame.dump()
    return w_result
