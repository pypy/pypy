import py
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.test.runner_test import LLtypeBackendTest,\
     boxfloat, constfloat
from rpython.jit.metainterp.history import BasicFailDescr, BasicFinalDescr
from rpython.jit.metainterp.resoperation import (ResOperation, rop,
                                                 InputArgInt)
from rpython.jit.tool.oparser import parse
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper import rclass
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import JitCellToken, TargetToken
from rpython.jit.codewriter import longlong


CPU = getcpuclass()

class FakeStats(object):
    pass


class TestARM64(LLtypeBackendTest):

    # for the individual tests see
    # ====> ../../test/runner_test.py

    #add_loop_instructions = 'ldr; adds; cmp; beq; b;'
    #if arch_version == 7:
    #    bridge_loop_instructions = ('ldr; movw; nop; cmp; bge; '
    #                                'push; movw; movt; push; movw; movt; '
    #                                'blx; movw; movt; bx;')
    #else:
    #    bridge_loop_instructions = ('ldr; mov; nop; nop; nop; cmp; bge; '
    #                                'push; ldr; mov; '
    #                                '[^;]+; ' # inline constant
    #                                'push; ldr; mov; '
    #                                '[^;]+; ' # inline constant
    #                                'blx; ldr; mov; '
    #                                '[^;]+; ' # inline constant
    #                                'bx;')

    def get_cpu(self):
        cpu = CPU(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu
