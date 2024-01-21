#!/usr/bin/env python

from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.test.runner_test import LLtypeBackendTest

CPU = getcpuclass()


class FakeStats(object):
    pass


class TestRISCV(LLtypeBackendTest):
    # for the individual tests see
    # ====> ../../test/runner_test.py

    def get_cpu(self):
        cpu = CPU(rtyper=None, stats=FakeStats())
        cpu.setup_once()
        return cpu

    # `test_compile_asmlen` expected outputs
    add_loop_instructions = (
        'ld; '  # same_as
        + 'add; '  # int_add
        + 'bnez; j; '  # guard_true
        + 'j; '  # jump
        + 'ebreak;')
    bridge_loop_instructions = (
        # Load the current frame depth
        'ld; '
        # Load the expected frame depth
        + 'li; (nop; )*'
        # Compare current to expected frame depth
        + 'bge; '
        # Store gcmap to jf_gcmap
        + '(((auipc; )*ld; )|((lui; )*addiw*; ))'
        + 'sd; '
        # Branch to frame_realloc_slowpath
        + '(((auipc; )*ld; )|((lui; )*addiw*; ))'
        + 'jalr; '
        # Jump to a target token
        + '(((auipc; )*ld; )|((lui; )*addiw*; ))'
        + 'jr; '
        + 'ebreak;')
