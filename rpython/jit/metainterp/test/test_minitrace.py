from rpython.jit.metainterp.minitrace import *
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
                elif opcode == "-":
                    acc -= 1
                elif opcode == "r":
                    return acc
                pc += 1
            return acc
        self.mini_interp(f, [1, 0])

        assert valueapi.get_value_int(self.metainterp.return_value) == 2
