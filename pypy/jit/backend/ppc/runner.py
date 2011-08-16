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
        self.fail_boxes_int = values_array(lltype.Signed, 1000)

        # floats are not supported yet
        self.supports_floats = False
        self.total_compiled_loops = 0
        self.total_compiled_bridges = 0

    # compile a given trace
    def compile_loop(self, inputargs, operations, looptoken, log=True):
        self.saved_descr = {}
        self.patch_list = []
        self.reg_map = {}
        self.fail_box_count = 0

        codebuilder = PPCBuilder()
        
        # initialize registers from memory
        self.next_free_register = 3
        for index, arg in enumerate(inputargs):
            self.reg_map[arg] = self.next_free_register
            addr = self.fail_boxes_int.get_addr_for_num(index)
            codebuilder.load_from(self.next_free_register, addr)
            self.next_free_register += 1
        
        self.startpos = codebuilder.get_relative_pos()

        self._walk_trace_ops(codebuilder, operations)
        self._make_epilogue(codebuilder)

        f = codebuilder.assemble()
        looptoken.ppc_code = f
        looptoken.codebuilder = codebuilder
        self.total_compiled_loops += 1
        self.teardown()

    def compile_bridge(self, descr, inputargs, operations, looptoken):
        self.saved_descr = {}
        self.patch_list = []
        self.reg_map = {}
        self.fail_box_count = 0

        codebuilder = looptoken.codebuilder
        # jump to the bridge
        current_pos = codebuilder.get_relative_pos()
        offset = current_pos - descr.patch_pos
        codebuilder.b(offset)
        codebuilder.patch_op(descr.patch_op)

        # initialize registers from memory
        self.next_free_register = 3
        use_index = 0
        for index, arg in enumerate(inputargs):
            self.reg_map[arg] = self.next_free_register
            addr = self.fail_boxes_int.get_addr_for_num(
                    descr.used_mem_indices[use_index])
            codebuilder.load_from(self.next_free_register, addr)
            self.next_free_register += 1
            use_index += 1
            
        self._walk_trace_ops(codebuilder, operations)
        self._make_epilogue(codebuilder)

        f = codebuilder.assemble()
        looptoken.ppc_code = f
        looptoken.codebuilder = codebuilder

        self.total_compiled_bridges += 1
        self.teardown()

    def get_next_register(self):
        reg = self.next_free_register
        self.next_free_register += 1
        return reg

    def _make_epilogue(self, codebuilder):
        for op_index, fail_index, guard, reglist in self.patch_list:
            curpos = codebuilder.get_relative_pos()
            offset = curpos - (4 * op_index)
            assert (1 << 15) > offset
            codebuilder.beq(offset)
            codebuilder.patch_op(op_index)

            # store return parameters in memory
            used_mem_indices = []
            for index, reg in enumerate(reglist):
                self.fail_box_count += 1
                # if reg is None, then there is a hole in the failargs
                if reg is not None:
                    addr = self.fail_boxes_int.get_addr_for_num(index)
                    codebuilder.store_reg(reg, addr)
                    used_mem_indices.append(index)

            patch_op = codebuilder.get_number_of_ops()
            patch_pos = codebuilder.get_relative_pos()
            descr = self.saved_descr[fail_index]
            descr.patch_op = patch_op
            descr.patch_pos = patch_pos
            descr.used_mem_indices = used_mem_indices

            codebuilder.li(3, fail_index)            
            codebuilder.blr()

    # set value in fail_boxes_int
    def set_future_value_int(self, index, value_int):
        self.fail_boxes_int.setitem(index, value_int)

    def clear_latest_values(self, count):
        for index in range(count):
            self.fail_boxes_int.setitem(index, 0)

    # executes the stored machine code in the token
    def execute_token(self, looptoken):   
        descr_index = looptoken.ppc_code()
        return self.saved_descr[descr_index]

    # return the number of values that can be returned
    def get_latest_value_count(self):
        return self.fail_box_count

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

    def teardown(self):
        self.patch_list = None
        self.reg_map = None
