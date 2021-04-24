#!/usr/bin/env python

from rpython.jit.backend.riscv.opassembler import OpAssembler


class AssemblerRISCV(OpAssembler):
    def __init__(self, cpu, translate_support_code=False):
        OpAssembler.__init__(self, cpu, translate_support_code)

    def _build_failure_recovery(self, exc, withfloats=False):
        pass

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        """Build write barrier slow path"""
        pass

    def build_frame_realloc_slowpath(self):
        pass

    def _build_propagate_exception_path(self):
        pass

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        pass

    def _build_stack_check_slowpath(self):
        pass

    def assemble_loop(self, jd_id, unique_id, logger, loopname, inputargs,
                      operations, looptoken, log):
        pass
