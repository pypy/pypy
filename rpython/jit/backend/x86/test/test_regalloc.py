""" explicit integration tests for register allocation in the x86 backend """

import pytest

from rpython.jit.backend.llsupport.test import test_regalloc_integration
from rpython.jit.backend.x86.assembler import Assembler386

class LogEntry(object):
    def __init__(self, position, name, *args):
        self.position = position
        self.name = name
        self.args = args

    def __repr__(self):
        r = repr(self.args)
        if self.name == "op":
            r = repr(self.args[1:])
            return "<%s: %s %s %s>" % (self.position, self.name, self.args[0], r.strip("(),"))
        return "<%s: %s %s>" % (self.position, self.name, r.strip("(),"))

class LoggingAssembler(Assembler386):
    def __init__(self, *args, **kwargs):
        self._instr_log = []
        Assembler386.__init__(self, *args, **kwargs)

    def _log(self, name, *args):
        self._instr_log.append(LogEntry(self._regalloc.rm.position, name, *args))

    def mov(self, from_loc, to_loc):
        self._log("mov", from_loc, to_loc)
        return Assembler386.mov(self, from_loc, to_loc)

    def regalloc_mov(self, from_loc, to_loc):
        self._log("mov", from_loc, to_loc)
        return Assembler386.mov(self, from_loc, to_loc)

    def regalloc_perform(self, op, arglocs, resloc):
        self._log("op", op.getopname(), arglocs, resloc)
        return Assembler386.regalloc_perform(self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        self._log("op", op.getopname(), arglocs)
        return Assembler386.regalloc_perform_discard(self, op, arglocs)

    def regalloc_perform_guard(self, guard_op, faillocs, arglocs, resloc,
                               frame_depth):
        self._log("guard", guard_op.getopname(), arglocs, faillocs, resloc)
        return Assembler386.regalloc_perform_guard(self, guard_op, faillocs,
                arglocs, resloc, frame_depth)


class TestCheckRegistersExplicitly(test_regalloc_integration.BaseTestRegalloc):
    def setup_class(cls):
        cls.cpu.assembler = LoggingAssembler(cls.cpu, False)
        cls.cpu.assembler.setup_once()

    def setup_method(self, meth):
        self.cpu.assembler._instr_log = self.log = []

    def teardown_method(self, meth):
        for l in self.log:
            print l

    def filter_log_moves(self):
        return [entry for entry in self.log if entry.name == "mov"]

    def test_unused(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1) # unused
        i9 = int_add(i2, i3)
        finish(i9)
        '''
        # does not crash
        self.interpret(ops, [5, 6, 7, 8])
        assert len([entry for entry in self.log if entry.args[0] == "int_add"]) == 1

    def test_bug_const(self):
        ops = '''
        [i0, i1, i2, i3]
        i9 = int_add(1, i3)
        finish(i9)
        '''
        # does not crash
        self.interpret(ops, [5, 6, 7, 8])
        assert len([entry for entry in self.log if entry.args[0] == "int_add"]) == 1

    def test_use_lea_even_for_stack(self):
        ops = '''
        [i0, i1, i2, i3]
        i9 = int_add(i3, 16)
        i4 = int_add(i3, 26)
        i6 = int_add(i9, i4)
        finish(i6)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        assert len(self.filter_log_moves()) == 2

    def test_call_use_correct_regs(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1)
        i8 = int_add(i2, 13)
        i9 = call_i(ConstClass(f1ptr), i7, descr=f1_calldescr)
        i10 = int_is_true(i9)
        guard_true(i10) [i8]
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        # two moves are needed from the stack frame to registers for arguments
        # i0 and i1, one for the result to the stack
        assert len(self.filter_log_moves()) == 3

    def test_call_use_argument_twice(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1)
        i8 = int_add(i2, 13)
        i9 = call_i(ConstClass(f2ptr), i7, i7, descr=f2_calldescr)
        i10 = int_is_true(i9)
        guard_true(i10) [i8]
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        # two moves are needed from the stack frame to registers for arguments
        # i0 and i1, one for the result to the stack
        # one for the copy to the other argument register
        assert len(self.filter_log_moves()) == 4

    @pytest.mark.skip("later")
    def test_same_stack_entry_many_times(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1)
        i8 = int_add(i2, i1)
        i9 = int_add(i3, i1)
        i10 = int_is_true(i9)
        guard_true(i10) [i8]
        finish(i7)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        # 4 moves for arguments, 1 for result
        assert len(self.filter_log_moves()) == 5

    def test_coalescing(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1)
        i8 = int_add(i7, i3)
        i9 = call_i(ConstClass(f1ptr), i8, descr=f1_calldescr)
        i10 = int_is_true(i9)
        guard_true(i10) []
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        # coalescing makes sure that i0 (and thus i71) lands in edi
        assert len(self.filter_log_moves()) == 2

    def test_coalescing_mul(self):
        # won't test all operations, but at least check a second one
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_mul(i0, i1)
        i8 = int_mul(i7, i3)
        i9 = call_i(ConstClass(f1ptr), i8, descr=f1_calldescr)
        i10 = int_is_true(i9)
        guard_true(i10) []
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        assert len(self.filter_log_moves()) == 2

    def test_lshift(self):
        ops = '''
        [i0, i1, i2, i3]
        i5 = int_add(i2, i3)
        i7 = int_lshift(i0, i5)
        i8 = int_lshift(i7, i3)
        i9 = call_i(ConstClass(f1ptr), i8, descr=f1_calldescr)
        i10 = int_is_true(i9)
        guard_true(i10) []
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        # 3 moves for arguments, 1 move for result
        assert len(self.filter_log_moves()) == 4

    def test_binop_dont_swap_unnecessarily(self):
        ops = '''
        [i0, i1, i2, i3]
        i7 = int_add(i0, i1)
        i8 = int_add(i2, 13)
        i9 = int_add(i7, i8)
        i10 = int_is_true(i9)
        guard_true(i10) []
        finish(i9)
        '''
        self.interpret(ops, [5, 6, 7, 8])
        add1 = self.log[2]
        op = self.log[5]
        assert op.name == "op"
        # make sure that the arguments of the third op are not swapped (since
        # that would break coalescing between i7 and i9)
        assert op.args[1][0] is add1.args[-1]
