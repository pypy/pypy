import math
import sys

import py
import pytest
import weakref

from rpython.rlib import rgc
from rpython.jit.codewriter.policy import StopAtXPolicy
from rpython.jit.metainterp import history
from rpython.jit.metainterp.test.support import LLJitMixin, noConst, get_stats
from rpython.jit.metainterp.warmspot import get_stats
from rpython.jit.metainterp.pyjitpl import MetaInterp
from rpython.rlib import rerased
from rpython.rlib.jit import (JitDriver, we_are_jitted, hint, dont_look_inside,
    loop_invariant, elidable, promote, jit_debug, assert_green,
    AssertGreenFailed, unroll_safe, current_trace_length, look_inside_iff,
    isconstant, isvirtual, set_param, record_exact_class, not_in_trace)
from rpython.rlib.longlong2float import float2longlong, longlong2float
from rpython.rlib.rarithmetic import ovfcheck, is_valid_int, int_force_ge_zero
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.tl.threadedcode.tla import TStack, t_push, t_empty, t_is_empty
from rpython.jit.tl.threadedcode.frame import Frame


def compile_threaded_code():
    pass

class BasicTests:
    @pytest.mark.skip(reason="currently the case that red variables are"
                      "number cannot work correctly")
    def test_minilang_num_1(self):

        @dont_look_inside
        def lt(lhs, rhs):
            if lhs < rhs:
                return 1
            else:
                return 0

        @dont_look_inside
        def add(x, y):
            return x + y

        @dont_look_inside
        def sub(x, y):
            return x - y

        @dont_look_inside
        def is_true(x):
            return x > 0

        @dont_look_inside
        def emit_jump(x, y, z):
            return x

        @dont_look_inside
        def emit_ret(x, y):
            return x

        ADD = 0
        SUB = 1
        LT = 2
        JUMP = 3
        JUMP_IF = 4
        EXIT = 5
        NOP = -100
        inst_set = {
            0: "ADD",
            1: "SUB",
            2: "LT",
            3: "JUMP",
            4: "JUMP_IF",
            5: "EXIT",
            -100: "NOP"
        }
        def opcode_to_string(pc, bytecode, tstack):
            op = bytecode[pc]
            name = inst_set.get(op)
            return "%s: %s, tstack top: %s" % (pc, name, tstack.pc)

        myjitdriver = JitDriver(greens=['pc', 'bytecode', 'tstack'], reds=['x',],
                                get_printable_location=opcode_to_string,
                                threaded_code_gen=True)
        def interp(x):
            tstack = TStack(-100, None)
            pc = 0
            # bytecode = [NOP, JUMP_IF, 5, JUMP, 8, SUB, JUMP, 1, EXIT]
            bytecode = [NOP, SUB, JUMP_IF, 1, EXIT]
            while True:
                myjitdriver.jit_merge_point(pc=pc, bytecode=bytecode, tstack=tstack, x=x)
                op = bytecode[pc]
                pc += 1
                if op == ADD:
                    x = add(x, 1)
                elif op == SUB:
                    x = sub(x, 1)
                elif op == JUMP:
                    t = int(bytecode[pc])
                    if we_are_jitted():
                        if t_is_empty(tstack):
                            pc = t
                        else:
                            pc, tstack = tstack.t_pop()
                            pc = emit_jump(pc, t, None)
                    else:
                        if t < pc:
                            myjitdriver.can_enter_jit(pc=t, bytecode=bytecode, tstack=tstack, x=x)
                        pc = t
                elif op == JUMP_IF:
                    t = int(bytecode[pc])
                    if is_true(x):
                        if we_are_jitted():
                            pc += 1
                            if not t < pc:
                                tstack = t_push(pc, tstack)
                            pc = emit_jump(pc, t, None)
                        else:
                            if t < pc:
                                myjitdriver.can_enter_jit(pc=t, bytecode=bytecode, tstack=tstack, x=x)
                            pc = t
                    else:
                        if we_are_jitted():
                            tstack = t_push(t, tstack)
                        pc += 1
                elif op == EXIT:
                    if we_are_jitted():
                        if t_is_empty(tstack):
                            return x
                        else:
                            pc, tstack = tstack.t_pop()
                            pc = emit_ret(pc, x)
                    else:
                        return x

        interp.oopspec = 'jit.not_in_trace()'
        res = self.meta_interp(interp, [100])

    def test_minilang_stack_1(self):

        @dont_look_inside
        def emit_jump(x, y, z):
            return x

        @dont_look_inside
        def emit_ret(x, y):
            return x

        ADD = 10; SUB = 11; LT = 12; JUMP = 13; JUMP_IF = 14; EXIT = 15; DUP = 16; CONST = 17
        NOP = -100
        inst_set = {
            10: "ADD",
            11: "SUB",
            12: "LT",
            13: "JUMP",
            14: "JUMP_IF",
            15: "EXIT",
            16: "DUP",
            17: "CONST",
            -100: "NOP"
        }
        def opcode_to_string(pc, entry_state, bytecode, tstack):
            op = bytecode[pc]
            name = inst_set.get(op)
            return "%s: %s, tstack top: %s" % (pc, name, tstack.pc)

        myjitdriver = JitDriver(greens=['pc', 'entry_state', 'bytecode', 'tstack'], reds=['frame'],
                                get_printable_location=opcode_to_string,
                                threaded_code_gen=True)

        # ideal case
        def compiled_test(frame):
            while True:
                frame.nop()
                frame.dup()
                if frame.is_true():
                    # true branch
                    frame.const_int(1)
                    frame.sub()
                else:
                    return frame.pop()

        saved_stack = [0] * Frame.size
        saved_sp = 0

        @not_in_trace
        def save_state(frame):
            saved_sp = frame.sp
            for i in range(Frame.size):
                saved_stack[i] = frame.stack[i]

        @not_in_trace
        def restore_state(frame):
            for i in range(Frame.size):
                frame.stack[i] = saved_stack[i]
            frame.sp = saved_sp

        def interp(x):
            tstack = TStack(-100, None)
            pc = 0
            bytecode = [ NOP,
                         DUP,
                         CONST, 1,
                         LT,
                         JUMP_IF, 9,
                         JUMP, 14,
                         CONST, 1,
                         SUB,
                         JUMP, 1,
                         EXIT ]

            frame = Frame(bytecode)
            frame.push(x)
            entry_state = pc, tstack
            while True:
                myjitdriver.jit_merge_point(pc=pc, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                            frame=frame)
                op = bytecode[pc]
                pc += 1
                if op == CONST:
                    v = int(bytecode[pc])
                    frame.const_int(v)
                    pc += 1
                elif op == DUP:
                    frame.dup()
                elif op == ADD:
                    frame.add()
                elif op == SUB:
                    frame.sub()
                elif op == LT:
                    frame.lt()
                elif op == JUMP:
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
                            save_state(frame)
                            myjitdriver.can_enter_jit(pc=t, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                      frame=frame)
                        pc = t
                elif op == JUMP_IF:
                    t = int(bytecode[pc])
                    if frame.is_true():
                        if we_are_jitted():
                            pc += 1
                            tstack = t_push(pc, tstack)
                        else:
                            if t < pc:
                                entry_state = t, tstack
                                save_state(frame)
                                myjitdriver.can_enter_jit(pc=t, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                          frame=frame)
                        pc = t
                    else:
                        if we_are_jitted():
                            tstack = t_push(t, tstack)
                        pc += 1
                elif op == EXIT:
                    if we_are_jitted():
                        if t_is_empty(tstack):
                            v = frame.pop()
                            pc = emit_ret(pc, v)
                            pc, tstack = entry_state
                            restore_state(frame)
                            myjitdriver.can_enter_jit(pc=pc, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                      frame=frame)
                        else:
                            pc, tstack = tstack.t_pop()
                            v = frame.pop()
                            pc = emit_ret(pc, v)
                    else:
                        return frame.pop()

        interp.oopspec = 'jit.not_in_trace()'
        res = self.meta_interp(interp, [100])

    def test_minilang_stack_2(self):

        @dont_look_inside
        def emit_jump(x, y, z):
            return x

        @dont_look_inside
        def emit_ret(x, y):
            return x

        ADD = 10; SUB = 11; LT = 12; JUMP = 13; JUMP_IF = 14;  EXIT = 15
        DUP = 16; CONST = 17;  NOP = -100
        inst_set = {
            10: "ADD",
            11: "SUB",
            12: "LT",
            13: "JUMP",
            14: "JUMP_IF",
            15: "EXIT",
            16: "DUP",
            17: "CONST",
            -100: "NOP"
        }

        def opcode_to_string(pc, entry_state, bytecode, tstack):
            op = bytecode[pc]
            name = inst_set.get(op)
            return "%s: %s, tstack top: %s" % (pc, name, tstack.pc)

        myjitdriver = JitDriver(greens=['pc', 'entry_state', 'bytecode', 'tstack'], reds=['frame'],
                                get_printable_location=opcode_to_string,
                                threaded_code_gen=True)

        saved_stack = [0] * Frame.size
        saved_sp = 0

        @not_in_trace
        def save_state(frame):
            saved_sp = frame.sp
            for i in range(Frame.size):
                saved_stack[i] = frame.stack[i]

        @not_in_trace
        def restore_state(frame):
            for i in range(Frame.size):
                frame.stack[i] = saved_stack[i]
            frame.sp = saved_sp

        def interp(x):
            tstack = TStack(-100, None)
            pc = 0
            bytecode = [ DUP,
                         CONST, 0,
                         LT,
                         JUMP_IF, 8,
                         JUMP, 13,
                         CONST, 1,
                         SUB,
                         JUMP, 0,
                         CONST, 1000,
                         SUB,
                         EXIT ]

            frame = Frame(bytecode)
            frame.push(x)
            entry_state = pc, tstack
            while True:
                myjitdriver.jit_merge_point(pc=pc, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                            frame=frame)
                op = bytecode[pc]
                pc += 1
                if op == CONST:
                    v = int(bytecode[pc])
                    frame.const_int(v)
                    pc += 1
                elif op == DUP:
                    frame.dup()
                elif op == ADD:
                    frame.add()
                elif op == SUB:
                    frame.sub()
                elif op == LT:
                    frame.lt()
                elif op == JUMP:
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
                            save_state(frame)
                            myjitdriver.can_enter_jit(pc=t, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                      frame=frame)
                        pc = t
                elif op == JUMP_IF:
                    t = int(bytecode[pc])
                    if frame.is_true():
                        if we_are_jitted():
                            pc += 1
                            tstack = t_push(pc, tstack)
                        else:
                            if t < pc:
                                entry_state = t, tstack
                                save_state(frame)
                                myjitdriver.can_enter_jit(pc=t, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                          frame=frame)
                        pc = t
                    else:
                        if we_are_jitted():
                            tstack = t_push(t, tstack)
                        pc += 1
                elif op == EXIT:
                    if we_are_jitted():
                        if t_is_empty(tstack):
                            v = frame.pop()
                            pc = emit_ret(pc, v)
                            pc, tstack = entry_state
                            restore_state(frame)
                            myjitdriver.can_enter_jit(pc=pc, entry_state=entry_state, bytecode=bytecode, tstack=tstack,
                                                      frame=frame)
                        else:
                            pc, tstack = tstack.t_pop()
                            v = frame.pop()
                            pc = emit_ret(pc, v)
                    else:
                        return frame.pop()

        interp.oopspec = 'jit.not_in_trace()'
        res = self.meta_interp(interp, [100])

class TestLLtype(BasicTests, LLJitMixin):
    pass
