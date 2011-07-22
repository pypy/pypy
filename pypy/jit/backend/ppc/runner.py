import py
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp import history, compile
from pypy.jit.backend.x86.assembler import Assembler386
from pypy.jit.backend.x86.arch import FORCE_INDEX_OFS
from pypy.jit.backend.x86.profagent import ProfileAgent
from pypy.jit.backend.llsupport.llmodel import AbstractLLCPU
from pypy.jit.backend.x86 import regloc
from pypy.jit.backend.x86.support import values_array
from pypy.jit.backend.ppc.ppcgen.ppc_assembler import PPCBuilder
import sys

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('jitbackend')
py.log.setconsumer('jitbackend', ansi_log)


class PPC_64_CPU(AbstractLLCPU):

    def __init__(self, rtyper, stats, opts=None, translate_support_code=False,
                 gcdescr=None):
        if gcdescr is not None:
            gcdescr.force_index_ofs = FORCE_INDEX_OFS
        AbstractLLCPU.__init__(self, rtyper, stats, opts,
                               translate_support_code, gcdescr)

        # pointer to an array of ints
        # XXX length of the integer array is 1000 for now
        self.arg_to_box = {}
        self.fail_boxes_int = values_array(lltype.Signed, 1000)
        self.saved_descr = {}

        # floats are not supported yet
        self.supports_floats = False

    # compile a given trace
    def compile_loop(self, inputargs, operations, looptoken, log=True):
        codebuilder = PPCBuilder()
        self.saved_descr[len(self.saved_descr)] = operations[-1].getdescr()

        for index, arg in enumerate(inputargs):
            self.arg_to_box[arg] = index
            
        self._walk_trace_ops(codebuilder, operations)

        f = codebuilder.assemble()
        looptoken.ppc_code = f

    def set_future_value_int(self, index, value_int):
        self.fail_boxes_int.setitem(index, value_int)

    # executes the stored machine code in the token
    def execute_token(self, looptoken):   
        descr_index = looptoken.ppc_code()
        return self.saved_descr[descr_index]

    # fetch the result of the computation and return it
    def get_latest_value_int(self, index):
        value = self.fail_boxes_int.getitem(index)
        return value

    # walk through the given trace and generate machine code
    def _walk_trace_ops(self, codebuilder, operations):
        for op in operations:
            codebuilder.build_op(op, self)
                
    def get_box_index(self, box):
        return self.arg_to_box[box]
