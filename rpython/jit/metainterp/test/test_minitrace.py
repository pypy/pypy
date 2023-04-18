from rpython.jit.metainterp.minitrace import *

def test_int_add():
    history = History(2)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    r1 = miframe.opimpl_int_add(0, 1, 2)
    r2 = miframe.opimpl_int_add(1, 2, 3)

    assert r1 is miframe.registers_i[2]
    assert r2 is miframe.registers_i[3]

    assert r1.getint() == 22
    assert metainterp.history.trace == [(rop.INT_ADD, [i1, i2], None), (rop.INT_ADD, [i2, r1], None)]

def test_int_add_const():
    history = History(0)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    miframe.registers_i[0] = ConstInt(15)
    miframe.registers_i[1] = ConstInt(7)

    r1 = miframe.opimpl_int_add(0, 1, 2)

    assert r1 is miframe.registers_i[2]
    assert r1.getint() == 22
    assert r1.is_constant()
    assert metainterp.history.trace == []

def test_simulate_call():
    history = History(2)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    # setup inputs 0, 1
    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    # add 0, 1 = 2
    r1 = miframe.opimpl_int_add(0, 1, 2)

    # call function with args 2, 0 (function adds args)
    miframe2 = MIFrame(metainterp)
    metainterp.framestack.append(miframe2)
    miframe2.registers_i[0] = miframe.registers_i[2]
    miframe2.registers_i[1] = miframe.registers_i[0]
    r2 = miframe2.opimpl_int_add(0, 1, 2)

    # register 3 contains result
    miframe.registers_i[3] = miframe2.registers_i[2]

    # add 2 and 3 = 4
    r4 = miframe.opimpl_int_add(2, 3, 4)

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
        import pdb; pdb.set_trace()

    def test_first_loop(self):
        def f(x, y):
            res = 0
            while y > 0:
                res += x * x
                x += 1
                res += x * x
                y -= 1
            return res
        res = self.mini_interp(f, [6, 7])
