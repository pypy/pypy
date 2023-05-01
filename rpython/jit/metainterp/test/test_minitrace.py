from rpython.jit.metainterp.minitrace import *

class DummyJitcode:
    def __init__(self):
        self.code = "dummy" 

def test_int_add():
    metainterp = MetaInterp("dummy")
    metainterp.create_empty_history()
    miframe = MIFrame(metainterp, DummyJitcode())
    metainterp.framestack.append(miframe)

    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    metainterp.history.set_inputargs([i1, i2], "dummy")

    r1 = miframe.opimpl_int_add(i1, i2)

    # manually write result
    miframe.registers_i[2] = r1

    r2 = miframe.opimpl_int_add(i2, r1)

    assert r1.getint() == 22
    assert metainterp.history.trace == [(rop.INT_ADD, [i1, i2], None), (rop.INT_ADD, [i2, r1], None)]

def test_int_add_const():
    metainterp = MetaInterp("dummy")
    metainterp.create_empty_history()
    miframe = MIFrame(metainterp, DummyJitcode())
    metainterp.framestack.append(miframe)

    metainterp.history.set_inputargs([], "dummy")

    c1 = miframe.registers_i[0] = ConstInt(15)
    c2 = miframe.registers_i[1] = ConstInt(7)

    r1 = miframe.opimpl_int_add(c1, c2)

    assert r1.getint() == 22
    assert r1.is_constant()
    assert metainterp.history.trace == []

def test_simulate_call():
    metainterp = MetaInterp("dummy")
    metainterp.create_empty_history()
    miframe = MIFrame(metainterp, DummyJitcode())
    metainterp.framestack.append(miframe)

    # setup inputs 0, 1
    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    metainterp.history.set_inputargs([i1, i2], "dummy")

    # add 0, 1 = 2
    r1 = miframe.opimpl_int_add(i1, i2)

    # manually write result
    miframe.registers_i[2] = r1

    # call function with args 2, 0 (function adds args)
    miframe2 = MIFrame(metainterp, DummyJitcode())
    metainterp.framestack.append(miframe2)
    miframe2.registers_i[0] = miframe.registers_i[2]
    miframe2.registers_i[1] = miframe.registers_i[0]
    r2 = miframe2.opimpl_int_add(r1, i1)

    # manually write result
    miframe2.registers_i[2] = r2

    # register 3 contains result
    miframe.registers_i[3] = miframe2.registers_i[2]

    # add 2 and 3 = 4
    r4 = miframe.opimpl_int_add(r1, r2)

    assert r4.getint() == 59
    assert not r4.is_constant()
    assert metainterp.history.trace == [(rop.INT_ADD, [i1, i2], None), (rop.INT_ADD, [r1, i1], None), (rop.INT_ADD, [r1, r2], None)]


from rpython.rlib import jit
from rpython.jit.backend.llgraph import runner
from rpython.jit.metainterp.test import support


class TestMiniTrace(object):
    def mini_interp(self, function, args):
        stats = support._get_jitcodes(self, runner.LLGraphCPU, function, args)
        self._run_with_minitrace(args, stats)

    def _run_with_minitrace(self, args, stats):
        from rpython.jit.metainterp import pyjitpl, history, jitexc
        cw = self.cw
        opt = history.Options(listops=True)
        metainterp_sd = pyjitpl.MetaInterpStaticData(cw.cpu, opt)
        stats.metainterp_sd = metainterp_sd
        metainterp_sd.finish_setup(cw)
        metainterp_sd.finish_setup_descrs()

        [jitdriver_sd] = metainterp_sd.jitdrivers_sd
        miniinterp_staticdata(metainterp_sd, cw)
        metainterp = MetaInterp(metainterp_sd)
        jitdriver_sd, = metainterp_sd.jitdrivers_sd
        metainterp.compile_and_run_once(jitdriver_sd, *args)

        self.metainterp = metainterp

    #def test_first_loop(self):
    #    def f(x, y):
    #        res = 0
    #        while y > 0:
    #            res += x * x
    #            x += 1
    #            res += x * x
    #            y -= 1
    #        return res
    #    self.mini_interp(f, [6, 7])
    #
    #    # TODO assertions
    #    assert self.metainterp.framestack[-1].return_value.getint() == 1323
    #    assert len(self.metainterp.history.snapshots) == 7 + 1

    def test_interp(self):
        def f(bytecode_choice, init):
            if bytecode_choice == 1:
                bytecode = "+++++---r"
            else:
                bytecode = "r"
            pc = 0
            acc = init
            while pc < len(bytecode):
                opcode = bytecode[pc]
                if opcode == "+":
                    acc += 1
                if opcode == "-":
                    acc -= 1
                if opcode == "r":
                    return acc
                pc += 1
            return acc
        self.mini_interp(f, [1, 0])

        assert self.metainterp.return_value.getint() == 2
