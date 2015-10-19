from rpython.jit.backend.llsupport.assembler import GuardToken, BaseAssembler
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.zarch import locations as loc
from rpython.jit.backend.zarch.codebuilder import InstrBuilder
from rpython.jit.metainterp.resoperation import rop
from rpython.rlib.objectmodel import we_are_translated, specialize, compute_unique_id

class AssemblerZARCH(BaseAssembler):

    def __init__(self, cpu, translate_support_code=False):
        BaseAssembler.__init__(self, cpu, translate_support_code)
        self.mc = None
        self.pending_guards = None
        self.current_clt = None
        self._regalloc = None
        self.datablockwrapper = None
        self.propagate_exception_path = 0
        self.stack_check_slowpath = 0
        self.loop_run_counters = []
        self.gcrootmap_retaddr_forced = 0

    def setup(self, looptoken):
        BaseAssembler.setup(self, looptoken)
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        if we_are_translated():
            self.debug = False
        self.current_clt = looptoken.compiled_loop_token
        self.mc = InstrBuilder()
        self.pending_guards = []
        #assert self.datablockwrapper is None --- but obscure case
        # possible, e.g. getting MemoryError and continuing
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.mc.datablockwrapper = self.datablockwrapper
        self.target_tokens_currently_compiling = {}
        self.frame_depth_to_patch = []

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def gen_func_prolog(self):
        self.mc.STMG(reg.r0, reg.r15, loc.addr(reg.sp, -160))
        #self.mc.LAY(reg.r15, loc.addr(reg.sp, -160))

    def gen_func_epilog(self):
        self.mc.LMG(reg.r0, reg.r15, loc.addr(reg.sp, -160))
        self.jmpto(reg.r14)

    def jmpto(self, register):
        self.mc.BCR_rr(0xf, register.value)

    def _build_failure_recovery(self, exc, withfloats=False):
        pass # TODO

    def _build_wb_slowpath(self, withcards, withfloats=False, for_frame=False):
        pass # TODO

    def build_frame_realloc_slowpath(self):
        # this code should do the following steps
        # a) store all registers in the jitframe
        # b) fish for the arguments passed by the caller
        # c) store the gcmap in the jitframe
        # d) call realloc_frame
        # e) set the fp to point to the new jitframe
        # f) store the address of the new jitframe in the shadowstack
        # c) set the gcmap field to 0 in the new jitframe
        # g) restore registers and return
        pass # TODO

    def _build_propagate_exception_path(self):
        pass # TODO

    def _build_cond_call_slowpath(self, supports_floats, callee_only):
        """ This builds a general call slowpath, for whatever call happens to
        come.
        """
        pass # TODO

    def _build_stack_check_slowpath(self):
        pass # TODO
    # ________________________________________
    # ASSEMBLER EMISSION

    def emit_op_int_add(self, op):
        pass

def notimplemented_op(self, op, arglocs, regalloc, fcond):
    print "[ZARCH/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)

asm_operations = [notimplemented_op] * (rop._LAST + 1)
asm_extra_operations = {}

for name, value in AssemblerZARCH.__dict__.iteritems():
    if name.startswith('emit_op_'):
        opname = name[len('emit_op_'):]
        num = getattr(rop, opname.upper())
        asm_operations[num] = value
