import py
from rpython.jit.metainterp.history import BoxInt, ConstInt
from rpython.jit.metainterp.history import (BoxPtr, ConstPtr, BasicFailDescr,
                                            BasicFinalDescr)
from rpython.jit.metainterp.history import JitCellToken
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.codewriter import heaptracker
from rpython.jit.backend.llsupport.descr import GcCache
from rpython.jit.backend.llsupport.gc import GcLLDescription
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.tool.oparser import parse
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import rclass, rstr
from rpython.jit.backend.llsupport.gc import GcLLDescr_framework

from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.backend.ppc.runner import PPC_CPU
from rpython.jit.backend.ppc.test.test_runner import FakeStats

class TestAssembler(object):

    type_system = 'lltype'

    def setup_class(cls):
        cls.cpu = PPC_CPU(rtyper=None, stats=FakeStats())
        cls.cpu.setup_once()

    def interpret_direct_entry_point(self, ops, args, namespace):
        loop = self.parse(ops, namespace)
        looptoken = JitCellToken()
        self.cpu.compile_loop(loop.inputargs, loop.operations, looptoken)
        param_sign_list = []
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                param_sign_list.append(lltype.Signed)
            elif isinstance(arg, float):
                assert 0, "not implemented yet"
            else:
                assert 0, "not implemented yet"

        signature = lltype.FuncType(param_sign_list, lltype.Signed)
        fail_descr = self.cpu.execute_token(looptoken, *args)
        return fail_descr

    def parse(self, s, namespace, boxkinds=None):
        return parse(s, self.cpu, namespace,
                     type_system=self.type_system,
                     boxkinds=boxkinds)

    # XXX this test should also be used by the other backends
    def test_call_assembler_vary_arguments(self):
        namespace = {}
        numargs = 20

        for i in range(numargs + 1):
            namespace["fdescr%d" % i] = BasicFailDescr(i)
        namespace["finishdescr"] = BasicFinalDescr(numargs + 1)

        for i in range(1, numargs + 1):
            arglist = []
            guardlist = []

            for k in range(i):
                name = "i%d" % k
                arglist.append(name)
                guardlist.append("guard_value(%s, %d, descr=fdescr%d) [%s]"
                        % (name, k, k, name))

            argstr = "".join(("[", ", ".join(arglist), "]\n"))
            guardstr = "\n".join(guardlist) + "\n"
            finish = "finish(descr=finishdescr)\n"

            trace = "".join((argstr, guardstr, finish))
            fail_descr = self.interpret_direct_entry_point(trace, range(i), namespace)
            assert fail_descr.identifier == namespace["finishdescr"].identifier
