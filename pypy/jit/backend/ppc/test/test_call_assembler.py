import py
from pypy.jit.metainterp.history import BoxInt, ConstInt,\
     BoxPtr, ConstPtr, TreeLoop, BasicFailDescr
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.codewriter import heaptracker
from pypy.jit.backend.llsupport.descr import GcCache
from pypy.jit.backend.llsupport.gc import GcLLDescription
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import rclass, rstr
from pypy.jit.backend.llsupport.gc import GcLLDescr_framework, GcPtrFieldDescr

from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.backend.ppc.runner import PPC_CPU
from pypy.jit.backend.ppc.test.test_runner import FakeStats

class TestAssembler(object):

    type_system = 'lltype'

    def setup_class(cls):
        cls.cpu = PPC_CPU(rtyper=None, stats=FakeStats())
        cls.cpu.setup_once()

    def interpret_direct_entry_point(self, ops, args, namespace):
        loop = self.parse(ops, namespace)
        self.cpu.compile_loop(loop.inputargs, loop.operations, loop.token)
        param_sign_list = []
        for i, arg in enumerate(args):
            if isinstance(arg, int):
                param_sign_list.append(lltype.Signed)
            elif isinstance(arg, float):
                assert 0, "not implemented yet"
            else:
                assert 0, "not implemented yet"

        looptoken = loop.token
        signature = lltype.FuncType(param_sign_list, lltype.Signed)
        addr = looptoken._ppc_direct_bootstrap_code
        func = rffi.cast(lltype.Ptr(signature), addr)
        fail_index = func(*args)
        fail_descr = self.cpu.get_fail_descr_from_number(fail_index)
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
        namespace["finishdescr"] = BasicFailDescr(numargs + 1)

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
