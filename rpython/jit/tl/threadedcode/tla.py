from rpython.rlib import jit
from rpython.rlib.jit import JitDriver, we_are_jitted, we_are_translated
from rpython.jit.tl.threadedcode.traverse_stack import *
from rpython.jit.tl.threadedcode.tlib import *

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



class W_IntObject(W_Object):

    def __init__(self, intvalue):
        self.intvalue = intvalue

    def __repr__(self):
        return self.getrepr()

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

    def mod(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue % w_other.intvalue
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

    def gt(self, w_other):
        if isinstance(w_other, W_IntObject):
            if self.intvalue > w_other.intvalue:
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

class W_FloatObject(W_Object):

    def __init__(self, floatvalue):
        self.floatvalue = floatvalue

    def __repr__(self):
        return self.getrepr()

    def getrepr(self):
        return str(self.floatvalue)

    def is_true(self):
        return self.floatvalue != 0.0

    def add(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue + w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def sub(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue - w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def mul(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue * w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def div(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue / w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def mod(self, w_other):
        if isinstance(w_other, W_FloatObject):
            sum = self.floatvalue % w_other.floatvalue
            return W_FloatObject(sum)
        else:
            raise OperationError

    def eq(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue == w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def lt(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue < w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def gt(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue > w_other.floatvalue:
                return W_IntObject(1)
            else:
                return W_IntObject(0)
        else:
            raise OperationError

    def le(self, w_other):
        if isinstance(w_other, W_FloatObject):
            if self.floatvalue <= w_other.floatvalue:
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

from rpython.jit.tl.threadedcode.bytecode import *

def get_printable_location_tc(pc, entry_state, bytecode, tstack):
    op = ord(bytecode[pc])
    name = bytecodes[op]
    if hasarg[op]:
        arg = str(ord(bytecode[pc + 1]))
    else:
        arg = ''
    return "%s: %s %s" % (pc, name, arg)

def get_printable_location(pc, bytecode):
    return get_printable_location_tc(pc, 0, bytecode, t_empty())

tcjitdriver = JitDriver(
    greens=['pc', 'entry_state', 'bytecode', 'tstack'], reds=['self'],
    get_printable_location=get_printable_location_tc, threaded_code_gen=True)


tjjitdriver = JitDriver(
    greens=['pc', 'bytecode',], reds=['self'],
    get_printable_location=get_printable_location, is_recursive=True)


class Frame(object):

    def __init__(self, bytecode):
        self.bytecode = bytecode
        self.stack = [None] * 10240
        self.stackpos = 0

        self.saved_stack = [None] * 10240
        self.saved_stackpos = 0

    @jit.not_in_trace
    def save_state(self):
        self.saved_stackpos = self.stackpos
        for i in range(len(self.stack)):
            self.saved_stack[i] = self.stack[i]

    @jit.not_in_trace
    def restore_state(self):
        for i in range(len(self.stack)):
            self.stack[i] = self.saved_stack[i]
        self.stackpos = self.saved_stackpos

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
    def take(self,n):
        assert len(self.stack) is not 0
        return self.stack[self.stackpos - n - 1]

    @jit.dont_look_inside
    def drop(self, n):
        for _ in range(n):
            self.pop()

    @jit.not_in_trace
    def print_stack(self):
        out = "["
        for elem in self.stack:
            if elem is None:
                break
            out = "%s, %s" % (out, elem)
        out = "%s ]" % (out)
        print out

    @jit.dont_look_inside
    def is_true(self):
        w_x = self.pop()
        res = w_x.is_true()
        return res

    @jit.dont_look_inside
    def CONST_INT(self, pc):
        if isinstance(pc, int):
            x = ord(self.bytecode[pc])
            self.push(W_IntObject(x))
        else:
            raise OperationError

    @jit.dont_look_inside
    def CONST_FLOAT(self, pc):
        if isinstance(pc, float):
            x = ord(self.bytecode[pc])
            self.push(W_FloatObject(x))
        else:
            raise OperationError

    @jit.dont_look_inside
    def ADD(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.add(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def SUB(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.sub(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MUL(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mul(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DIV(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.div(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def MOD(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.mod(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def DUP(self):
        w_x = self.pop()
        self.push(w_x)
        self.push(w_x)

    @jit.dont_look_inside
    def DUPN(self, pc):
        n = ord(self.bytecode[pc])
        w_x = self.take(n)
        self.push(w_x)

    @jit.dont_look_inside
    def LT(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.lt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def GT(self):
        w_y = self.pop()
        w_x = self.pop()
        w_z = w_x.gt(w_y)
        self.push(w_z)

    @jit.dont_look_inside
    def EQ(self):
        w_y = self.pop()
        w_x = self.pop()
        self.push(w_x.eq(w_y))

    @jit.dont_look_inside
    def NE(self):
        w_y = self.pop()
        w_x = self.pop()
        if w_x.eq(w_y).intvalue:
            self.push(W_IntObject(1))
        else:
            self.push(W_IntObject(0))

    @jit.dont_look_inside
    def RETURN(self):
        return self.pop()

    @jit.dont_look_inside
    def CALL(self, t):
        res = self.interp(t)
        if res:
            self.push(res)

    @jit.dont_look_inside
    def CALL_NORMAL(self, t):
        res = self.interp_normal(t)
        _ = self.pop()
        if res:
            self.push(res)

    @jit.dont_look_inside
    def CALL_JIT(self, t):
        res = self.interp_jit(t)
        if res:
            self.push(res)

    @jit.dont_look_inside
    def RET(self, n):
        v = self.pop()
        for _ in range(n):
            self.pop()
        return v

    @jit.dont_look_inside
    def PRINT(self):
        v = self.pop()
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

    def _RETURN(self):
        return self._pop()

    def _CALL(self, t):
        res = self.interp(t)
        if res is not None:
            self._push(res)

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
        v = self.pop()
        print v

    def interp_jit(self, pc=0):
        bytecode = self.bytecode
        while pc < len(bytecode):
            tjjitdriver.jit_merge_point(pc=pc, bytecode=bytecode, self=self)

            # print get_printable_location(pc, bytecode)
            # self.print_stack()
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self._CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self._pop()

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
            # print get_printable_location_tc(pc, entry_state, bytecode, tstack)
            # self.print_stack()
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self.CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self.pop()

            elif opcode == DUP:
                self.DUP()

            elif opcode == DUPN:
                self.DUPN(pc)
                pc += 1

            elif opcode == LT:
                self.LT()

            elif opcode == GT:
                self.GT()

            elif opcode == EQ:
                self.EQ()

            elif opcode == ADD:
                self.ADD()

            elif opcode == SUB:
                self.SUB()

            elif opcode == DIV:
                self.DIV()

            elif opcode == MUL:
                self.MUL()

            elif opcode == MOD:
                self.MOD()

            elif opcode == CALL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_NORMAL(t)

            elif opcode == RET:
                argnum = ord(bytecode[pc])
                pc += 1
                return self.RET(argnum)

            elif opcode == JUMP:
                target = ord(bytecode[pc])
                pc = target

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                if self.is_true():
                    pc = target

            elif opcode == EXIT:
                return self.pop()

            elif opcode == PRINT:
                self.PRINT()

            else:
                assert False, 'Unknown opcode: %d' % opcode

    def interp(self, pc=0):
        tstack = t_empty()
        entry_state = pc
        bytecode = self.bytecode

        while pc < len(bytecode):
            tcjitdriver.jit_merge_point(bytecode=bytecode, entry_state=entry_state,
                                        pc=pc, tstack=tstack, self=self)
            # print get_printable_location_tc(pc, entry_state, bytecode, tstack)
            # self.print_stack()
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                self.CONST_INT(pc)
                pc += 1

            elif opcode == POP:
                self.pop()

            elif opcode == DUP:
                self.DUP()

            elif opcode == DUPN:
                self.DUPN(pc)
                pc += 1

            elif opcode == LT:
                self.LT()

            elif opcode == GT:
                self.GT()

            elif opcode == EQ:
                self.EQ()

            elif opcode == ADD:
                self.ADD()

            elif opcode == SUB:
                self.SUB()

            elif opcode == DIV:
                self.DIV()

            elif opcode == MUL:
                self.MUL()

            elif opcode == MOD:
                self.MOD()

            elif opcode == CALL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL(t)

            elif opcode == CALL_NORMAL:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_NORMAL(t)

            elif opcode == CALL_JIT:
                t = ord(bytecode[pc])
                pc += 1
                self.CALL_JIT(t)

            elif opcode == RET:
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.pop()
                        pc = entry_state;  self.restore_state()
                        pc = emit_ret(pc, w_x)
                        tcjitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=pc, tstack=tstack, self=self)
                    else:
                        pc, tstack = tstack.t_pop()
                        w_x = self.pop()
                        pc = emit_ret(pc, w_x)
                else:
                    argnum = ord(bytecode[pc])
                    return self.RET(argnum)

            elif opcode == JUMP:
                t = ord(bytecode[pc])
                pc += 1
                if we_are_jitted():
                    if tstack.t_is_empty():
                        pc = t
                    else:
                        pc, tstack = tstack.t_pop()
                    pc = emit_jump(pc, t)
                else:
                    if t < pc:
                        entry_state = t; self.save_state()
                        tcjitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=t, tstack=tstack, self=self)
                    pc = t

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                if we_are_jitted():
                    if self.is_true():
                        tstack = t_push(pc, tstack)
                        pc = target
                    else:
                        tstack = t_push(target, tstack)
                else:
                    if self.is_true():
                        if target < pc:
                            entry_state = target; self.save_state()
                            tcjitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                      pc=target, tstack=tstack, self=self)
                        pc = target

            elif opcode == EXIT:
                if we_are_jitted():
                    if tstack.t_is_empty():
                        w_x = self.pop()
                        pc = entry_state;  self.restore_state()
                        pc = emit_ret(pc, w_x)
                        tcjitdriver.can_enter_jit(bytecode=bytecode, entry_state=entry_state,
                                                  pc=pc, tstack=tstack, self=self)
                    else:
                        pc, tstack = tstack.t_pop()
                        w_x = self.pop()
                        pc = emit_ret(pc, w_x)
                else:
                    return self.pop()

            elif opcode == PRINT:
                self.PRINT()

            else:
                assert False, 'Unknown opcode: %s' % bytecodes[opcode]


def run(bytecode, w_arg, entry=None):
    frame = Frame(bytecode)
    frame.push(w_arg)
    if entry == "tracing" or entry == "tr":
        w_result = frame.interp_jit()
    else:
        w_result = frame.interp()
    return w_result
