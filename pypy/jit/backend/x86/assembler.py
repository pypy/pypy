import sys, os
from pypy.jit.backend.llsupport import symbolic
from pypy.jit.metainterp.history import Const, Box, BoxInt, BoxPtr, BoxFloat
from pypy.jit.metainterp.history import (AbstractFailDescr, INT, REF, FLOAT,
                                         LoopToken)
from pypy.rpython.lltypesystem import lltype, rffi, rstr, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper
from pypy.tool.uid import fixid
from pypy.jit.backend.x86.regalloc import (RegAlloc, X86RegisterManager,
                                           X86XMMRegisterManager, get_ebp_ofs,
                                           _get_scale)

from pypy.jit.backend.x86.arch import (FRAME_FIXED_SIZE, FORCE_INDEX_OFS, WORD,
                                       IS_X86_32, IS_X86_64)

from pypy.jit.backend.x86.regloc import (eax, ecx, edx, ebx,
                                         esp, ebp, esi, edi,
                                         xmm0, xmm1, xmm2, xmm3,
                                         xmm4, xmm5, xmm6, xmm7,
                                         r8, r9, r10, r11,
                                         r12, r13, r14, r15,
                                         X86_64_SCRATCH_REG,
                                         X86_64_XMM_SCRATCH_REG,
                                         RegLoc, StackLoc, ConstFloatLoc,
                                         ImmedLoc, AddressLoc, imm,
                                         imm0, imm1)

from pypy.rlib.objectmodel import we_are_translated, specialize
from pypy.jit.backend.x86 import rx86, regloc, codebuf
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.backend.x86.support import values_array
from pypy.rlib.debug import debug_print
from pypy.rlib import rgc
from pypy.jit.backend.x86.jump import remap_frame_layout
from pypy.rlib.streamio import open_file_as_stream
from pypy.jit.metainterp.history import ConstInt, BoxInt

# darwin requires the stack to be 16 bytes aligned on calls. Same for gcc 4.5.0,
# better safe than sorry
CALL_ALIGN = 16 // WORD

def align_stack_words(words):
    return (words + CALL_ALIGN - 1) & ~(CALL_ALIGN-1)

class MachineCodeBlockWrapper(object):
    MC_DEFAULT_SIZE = 1024*1024

    def __init__(self, assembler, bigsize, profile_agent=None):
        self.assembler = assembler
        self.old_mcs = [] # keepalive
        self.bigsize = bigsize
        self._mc = self._instantiate_mc()
        self.function_name = None
        self.profile_agent = profile_agent
        self.reset_reserved_bytes()

    def _instantiate_mc(self): # hook for testing
        return codebuf.MachineCodeBlock(self.bigsize)

    def ensure_bytes_available(self, num_bytes):
        if self.bytes_free() <= (self._reserved_bytes + num_bytes):
            self.make_new_mc()

    def reserve_bytes(self, num_bytes):
        self.ensure_bytes_available(num_bytes)
        self._reserved_bytes += num_bytes

    def reset_reserved_bytes(self):
        # XXX er.... pretty random number, just to be sure
        #     not to write half-instruction
        self._reserved_bytes = 64

    def get_relative_pos(self):
        return self._mc.get_relative_pos()

    def overwrite(self, pos, listofchars):
        return self._mc.overwrite(pos, listofchars)

    def bytes_free(self):
        return self._mc._size - self._mc.get_relative_pos()

    def start_function(self, name):
        self.function_name = name
        self.start_pos = self._mc.get_relative_pos()

    def end_function(self, done=True):
        assert self.function_name is not None
        size = self._mc.get_relative_pos() - self.start_pos
        address = self.tell() - size
        if self.profile_agent is not None:
            self.profile_agent.native_code_written(self.function_name,
                                                   address, size)
        if done:
            self.function_name = None

    def make_new_mc(self):
        new_mc = self._instantiate_mc()
        debug_print('[new machine code block at', new_mc.tell(), ']')

        if IS_X86_64:
            # The scratch register is sometimes used as a temporary
            # register, but the JMP below might clobber it. Rather than risk
            # subtle bugs, we preserve the scratch register across the jump.
            self._mc.PUSH_r(X86_64_SCRATCH_REG.value)
            
        self._mc.JMP(imm(new_mc.tell()))

        if IS_X86_64:
            # Restore scratch reg
            new_mc.POP_r(X86_64_SCRATCH_REG.value)

        if self.function_name is not None:
            self.end_function(done=False)
            self.start_pos = new_mc.get_relative_pos()

        self.assembler.write_pending_failure_recoveries()

        self._mc.done()
        self.old_mcs.append(self._mc)
        self._mc = new_mc
    make_new_mc._dont_inline_ = True

    def tell(self):
        return self._mc.tell()

    def done(self):
        self._mc.done()

def _new_method(name):
    def method(self, *args):
        if self.bytes_free() < self._reserved_bytes:
            self.make_new_mc()
        getattr(self._mc, name)(*args)    
    method.func_name = name
    return method

for _name in rx86.all_instructions + regloc.all_extra_instructions:
    setattr(MachineCodeBlockWrapper, _name, _new_method(_name))

for name in dir(codebuf.MachineCodeBlock):
    if name.upper() == name or name == "writechr":
        setattr(MachineCodeBlockWrapper, name, _new_method(name))

class GuardToken(object):
    def __init__(self, faildescr, failargs, fail_locs, exc, desc_bytes):
        self.faildescr = faildescr
        self.failargs = failargs
        self.fail_locs = fail_locs
        self.exc = exc
        self.desc_bytes = desc_bytes

    def recovery_stub_size(self):
        # XXX: 32 is pulled out of the air
        return 32 + len(self.desc_bytes)

DEBUG_COUNTER = lltype.Struct('DEBUG_COUNTER', ('i', lltype.Signed))

class Assembler386(object):
    mc = None
    mc_size = MachineCodeBlockWrapper.MC_DEFAULT_SIZE
    _float_constants = None
    _regalloc = None
    _output_loop_log = None

    def __init__(self, cpu, translate_support_code=False,
                            failargs_limit=1000):
        self.cpu = cpu
        self.verbose = False
        self.rtyper = cpu.rtyper
        self.malloc_func_addr = 0
        self.malloc_array_func_addr = 0
        self.malloc_str_func_addr = 0
        self.malloc_unicode_func_addr = 0
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.fail_boxes_float = values_array(lltype.Float, failargs_limit)
        self.fail_ebp = 0
        self.loop_run_counters = []
        # if we have 10000 loops, we have some other problems I guess
        self.float_const_neg_addr = 0
        self.float_const_abs_addr = 0
        self.malloc_fixedsize_slowpath1 = 0
        self.malloc_fixedsize_slowpath2 = 0
        self.pending_guard_tokens = None
        self.memcpy_addr = 0
        self.setup_failure_recovery()
        self._debug = False
        self.debug_counter_descr = cpu.fielddescrof(DEBUG_COUNTER, 'i')

    def leave_jitted_hook(self):
        ptrs = self.fail_boxes_ptr.ar
        llop.gc_assume_young_pointers(lltype.Void,
                                      llmemory.cast_ptr_to_adr(ptrs))

    def set_debug(self, v):
        self._debug = v

    def setup(self):
        if self.mc is None:
            # the address of the function called by 'new'
            gc_ll_descr = self.cpu.gc_ll_descr
            gc_ll_descr.initialize()
            ll_new = gc_ll_descr.get_funcptr_for_new()
            self.malloc_func_addr = rffi.cast(lltype.Signed, ll_new)
            if gc_ll_descr.get_funcptr_for_newarray is not None:
                ll_new_array = gc_ll_descr.get_funcptr_for_newarray()
                self.malloc_array_func_addr = rffi.cast(lltype.Signed,
                                                        ll_new_array)
            if gc_ll_descr.get_funcptr_for_newstr is not None:
                ll_new_str = gc_ll_descr.get_funcptr_for_newstr()
                self.malloc_str_func_addr = rffi.cast(lltype.Signed,
                                                      ll_new_str)
            if gc_ll_descr.get_funcptr_for_newunicode is not None:
                ll_new_unicode = gc_ll_descr.get_funcptr_for_newunicode()
                self.malloc_unicode_func_addr = rffi.cast(lltype.Signed,
                                                          ll_new_unicode)
            self.memcpy_addr = self.cpu.cast_ptr_to_int(codebuf.memcpy_fn)
            self.mc = MachineCodeBlockWrapper(self, self.mc_size, self.cpu.profile_agent)
            self._build_failure_recovery(False)
            self._build_failure_recovery(True)
            if self.cpu.supports_floats:
                self._build_failure_recovery(False, withfloats=True)
                self._build_failure_recovery(True, withfloats=True)
                codebuf.ensure_sse2_floats()
                self._build_float_constants()
            if hasattr(gc_ll_descr, 'get_malloc_fixedsize_slowpath_addr'):
                self._build_malloc_fixedsize_slowpath()
            s = os.environ.get('PYPYLOG')
            if s:
                if s.find(':') != -1:
                    s = s.split(':')[-1]
                self.set_debug(True)
                self._output_loop_log = s + ".count"
            # Intialize here instead of __init__ to prevent
            # pending_guard_tokens from being considered a prebuilt object,
            # which sometimes causes memory leaks since the prebuilt list is
            # still considered a GC root after we re-assign
            # pending_guard_tokens in write_pending_failure_recoveries
            self.pending_guard_tokens = []

    def finish_once(self):
        if self._debug:
            output_log = self._output_loop_log
            assert output_log is not None
            f = open_file_as_stream(output_log, "w")
            for i in range(len(self.loop_run_counters)):
                name, struct = self.loop_run_counters[i]
                f.write(str(name) + ":" +  str(struct.i) + "\n")
            f.close()

    def _build_float_constants(self):
        # 44 bytes: 32 bytes for the data, and up to 12 bytes for alignment
        addr = lltype.malloc(rffi.CArray(lltype.Char), 44, flavor='raw',
                             track_allocation=False)
        if not we_are_translated():
            self._keepalive_malloced_float_consts = addr
        float_constants = rffi.cast(lltype.Signed, addr)
        float_constants = (float_constants + 15) & ~15    # align to 16 bytes
        addr = rffi.cast(rffi.CArrayPtr(lltype.Char), float_constants)
        qword_padding = '\x00\x00\x00\x00\x00\x00\x00\x00'
        # 0x8000000000000000
        neg_const = '\x00\x00\x00\x00\x00\x00\x00\x80'
        # 0x7FFFFFFFFFFFFFFF
        abs_const = '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F'
        data = neg_const + qword_padding + abs_const + qword_padding
        for i in range(len(data)):
            addr[i] = data[i]
        self.float_const_neg_addr = float_constants
        self.float_const_abs_addr = float_constants + 16

    def _build_malloc_fixedsize_slowpath(self):
        # ---------- first helper for the slow path of malloc ----------
        self.malloc_fixedsize_slowpath1 = self.mc.tell()
        if self.cpu.supports_floats:          # save the XMM registers in
            for i in range(self.cpu.NUM_REGS):# the *caller* frame, from esp+8
                self.mc.MOVSD_sx((WORD*2)+8*i, i)
        self.mc.SUB_rr(edx.value, eax.value)       # compute the size we want
        if IS_X86_32:
            self.mc.MOV_sr(WORD, edx.value)        # save it as the new argument
        elif IS_X86_64:
            # rdi can be clobbered: its content was forced to the stack
            # by _fastpath_malloc(), like all other save_around_call_regs.
            self.mc.MOV_rr(edi.value, edx.value)

        addr = self.cpu.gc_ll_descr.get_malloc_fixedsize_slowpath_addr()
        self.mc.JMP(imm(addr))                    # tail call to the real malloc
        # ---------- second helper for the slow path of malloc ----------
        self.malloc_fixedsize_slowpath2 = self.mc.tell()
        if self.cpu.supports_floats:          # restore the XMM registers
            for i in range(self.cpu.NUM_REGS):# from where they were saved
                self.mc.MOVSD_xs(i, (WORD*2)+8*i)
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        self.mc.MOV(edx, heap(nursery_free_adr))   # load this in EDX
        self.mc.RET()
        self.mc.done()

    def assemble_loop(self, inputargs, operations, looptoken, log):
        """adds the following attributes to looptoken:
               _x86_loop_code       (an integer giving an address)
               _x86_bootstrap_code  (an integer giving an address)
               _x86_direct_bootstrap_code
               _x86_frame_depth
               _x86_param_depth
               _x86_arglocs
        """
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup()
        funcname = self._find_debug_merge_point(operations)
        if log:
            self._register_counter()
            operations = self._inject_debugging_code(operations)
        
        regalloc = RegAlloc(self, self.cpu.translate_support_code)
        arglocs = regalloc.prepare_loop(inputargs, operations, looptoken)
        looptoken._x86_arglocs = arglocs

        # profile support
        name = "Loop # %s: %s" % (looptoken.number, funcname)
        self.mc.start_function(name)
        looptoken._x86_bootstrap_code = self.mc.tell()
        adr_stackadjust = self._assemble_bootstrap_code(inputargs, arglocs)
        curadr = self.mc.tell()
        looptoken._x86_loop_code = curadr
        looptoken._x86_frame_depth = -1     # temporarily
        looptoken._x86_param_depth = -1     # temporarily        
        frame_depth, param_depth = self._assemble(regalloc, operations)
        self._patch_stackadjust(adr_stackadjust, frame_depth+param_depth)
        looptoken._x86_frame_depth = frame_depth
        looptoken._x86_param_depth = param_depth

        looptoken._x86_direct_bootstrap_code = self.mc.tell()
        self._assemble_bootstrap_direct_call(arglocs, curadr,
                                             frame_depth+param_depth)
        #
        debug_print("Loop #", looptoken.number, "has address",
                    looptoken._x86_loop_code, "to", self.mc.tell())
        self.mc.end_function()
        self.write_pending_failure_recoveries()
        
    def assemble_bridge(self, faildescr, inputargs, operations, log):
        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        self.setup()
        funcname = self._find_debug_merge_point(operations)
        if log:
            self._register_counter()
            operations = self._inject_debugging_code(operations)

        arglocs = self.rebuild_faillocs_from_descr(
            faildescr._x86_failure_recovery_bytecode)
        if not we_are_translated():
            assert ([loc.assembler() for loc in arglocs] ==
                    [loc.assembler() for loc in faildescr._x86_debug_faillocs])
        regalloc = RegAlloc(self, self.cpu.translate_support_code)
        operations = self._inject_debugging_code(operations)
        fail_depths = faildescr._x86_current_depths
        regalloc.prepare_bridge(fail_depths, inputargs, arglocs,
                                operations)

        # oprofile support
        descr_number = self.cpu.get_fail_descr_number(faildescr)
        name = "Bridge # %s: %s" % (descr_number, funcname)
        self.mc.start_function(name)

        adr_bridge = self.mc.tell()
        adr_stackadjust = self._patchable_stackadjust()
        frame_depth, param_depth = self._assemble(regalloc, operations)
        self._patch_stackadjust(adr_stackadjust, frame_depth+param_depth)
        if not we_are_translated():
            # for the benefit of tests
            faildescr._x86_bridge_frame_depth = frame_depth
            faildescr._x86_bridge_param_depth = param_depth
        # patch the jump from original guard
        self.patch_jump_for_descr(faildescr, adr_bridge)
        debug_print("Bridge out of guard",
                    descr_number,
                    "has address", adr_bridge, "to", self.mc.tell())
        self.mc.end_function()
        self.write_pending_failure_recoveries()

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guard_tokens:
            # Okay to write to _mc because we've already made sure that
            # there's enough space by "reserving" bytes.
            addr = self.generate_quick_failure(self.mc._mc, tok.faildescr, tok.failargs, tok.fail_locs, tok.exc, tok.desc_bytes)
            tok.faildescr._x86_adr_recovery_stub = addr
            self.patch_jump_for_descr(tok.faildescr, addr)

        self.pending_guard_tokens = []
        self.mc.reset_reserved_bytes()
        self.mc.done()

    def _find_debug_merge_point(self, operations):

        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                funcname = op.getarg(0)._get_str()
                break
        else:
            funcname = "<loop %d>" % len(self.loop_run_counters)
        # invent the counter, so we don't get too confused
        return funcname

    def _register_counter(self):
        if self._debug:
            struct = lltype.malloc(DEBUG_COUNTER, flavor='raw',
                                   track_allocation=False)   # known to leak
            struct.i = 0
            self.loop_run_counters.append((len(self.loop_run_counters), struct))
        
    def patch_jump_for_descr(self, faildescr, adr_new_target):
        adr_jump_offset = faildescr._x86_adr_jump_offset
        adr_recovery_stub = faildescr._x86_adr_recovery_stub
        offset = adr_new_target - (adr_jump_offset + 4)
        # If the new target fits within a rel32 of the jump, just patch
        # that. Otherwise, leave the original rel32 to the recovery stub in
        # place, but clobber the recovery stub with a jump to the real
        # target.
        if rx86.fits_in_32bits(offset):
            mc = codebuf.InMemoryCodeBuilder(adr_jump_offset, adr_jump_offset + 4)
            mc.writeimm32(offset)
        else:
            # "mov r11, addr; jmp r11" is 13 bytes
            mc = codebuf.InMemoryCodeBuilder(adr_recovery_stub, adr_recovery_stub + 13)
            mc.MOV_ri(X86_64_SCRATCH_REG.value, adr_new_target)
            mc.JMP_r(X86_64_SCRATCH_REG.value)

        mc.done()

    def _inject_debugging_code(self, operations):
        if self._debug:
            # before doing anything, let's increase a counter
            c_adr = ConstInt(rffi.cast(lltype.Signed,
                                     self.loop_run_counters[-1][1]))
            box = BoxInt()
            box2 = BoxInt()
            ops = [ResOperation(rop.GETFIELD_RAW, [c_adr],
                                box, descr=self.debug_counter_descr),
                   ResOperation(rop.INT_ADD, [box, ConstInt(1)], box2),
                   ResOperation(rop.SETFIELD_RAW, [c_adr, box2],
                                None, descr=self.debug_counter_descr)]
            operations = ops + operations
            # # we need one register free (a bit of a hack, but whatever)
            # self.mc.PUSH(eax)
            # adr = rffi.cast(lltype.Signed, self.loop_run_counters[-1][1])
            # self.mc.MOV(eax, heap(adr))
            # self.mc.ADD(eax, imm1)
            # self.mc.MOV(heap(adr), eax)
            # self.mc.POP(eax)
        return operations

    def _assemble(self, regalloc, operations):
        self._regalloc = regalloc
        regalloc.walk_operations(operations)        
        self.mc.done()
        if we_are_translated() or self.cpu.dont_keepalive_stuff:
            self._regalloc = None   # else keep it around for debugging
        frame_depth = regalloc.fm.frame_depth
        param_depth = regalloc.param_depth
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            target_frame_depth = jump_target_descr._x86_frame_depth
            target_param_depth = jump_target_descr._x86_param_depth
            frame_depth = max(frame_depth, target_frame_depth)
            param_depth = max(param_depth, target_param_depth)
        return frame_depth, param_depth

    def _patchable_stackadjust(self):
        # stack adjustment LEA
        self.mc.LEA32_rb(esp.value, 0)
        return self.mc.tell() - 4

    def _patch_stackadjust(self, adr_lea, reserved_depth):
        # patch stack adjustment LEA
        mc = codebuf.InMemoryCodeBuilder(adr_lea, adr_lea + 4)
        # Compute the correct offset for the instruction LEA ESP, [EBP-4*words].
        # Given that [EBP] is where we saved EBP, i.e. in the last word
        # of our fixed frame, then the 'words' value is:
        words = (self.cpu.FRAME_FIXED_SIZE - 1) + reserved_depth
        # align, e.g. for Mac OS X        
        aligned_words = align_stack_words(words+2)-2 # 2 = EIP+EBP
        mc.writeimm32(-WORD * aligned_words)
        mc.done()

    def _call_header(self):
        self.mc.PUSH_r(ebp.value)
        self.mc.MOV_rr(ebp.value, esp.value)
        for regloc in self.cpu.CALLEE_SAVE_REGISTERS:
            self.mc.PUSH_r(regloc.value)

        # NB. the shape of the frame is hard-coded in get_basic_shape() too.
        # Also, make sure this is consistent with FRAME_FIXED_SIZE.
        return self._patchable_stackadjust()

    def _call_footer(self):
        self.mc.LEA_rb(esp.value, -len(self.cpu.CALLEE_SAVE_REGISTERS) * WORD)

        for i in range(len(self.cpu.CALLEE_SAVE_REGISTERS)-1, -1, -1):
            self.mc.POP_r(self.cpu.CALLEE_SAVE_REGISTERS[i].value)

        self.mc.POP_r(ebp.value)
        self.mc.RET()

    def _assemble_bootstrap_direct_call(self, arglocs, jmpadr, stackdepth):
        if IS_X86_64:
            return self._assemble_bootstrap_direct_call_64(arglocs, jmpadr, stackdepth)
        # XXX pushing ebx esi and edi is a bit pointless, since we store
        #     all regsiters anyway, for the case of guard_not_forced
        # XXX this can be improved greatly. Right now it'll behave like
        #     a normal call
        nonfloatlocs, floatlocs = arglocs
        # XXX not to repeat the logic, a bit around
        adr_stackadjust = self._call_header()
        self._patch_stackadjust(adr_stackadjust, stackdepth)
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            if isinstance(loc, RegLoc):
                assert not loc.is_xmm
                self.mc.MOV_rb(loc.value, (2 + i) * WORD)
            loc = floatlocs[i]
            if isinstance(loc, RegLoc):
                assert loc.is_xmm
                self.mc.MOVSD_xb(loc.value, (1 + i) * 2 * WORD)
        tmp = eax
        xmmtmp = xmm0
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            if loc is not None and not isinstance(loc, RegLoc):
                self.mc.MOV_rb(tmp.value, (2 + i) * WORD)
                self.mc.MOV(loc, tmp)
            loc = floatlocs[i]
            if loc is not None and not isinstance(loc, RegLoc):
                self.mc.MOVSD_xb(xmmtmp.value, (1 + i) * 2 * WORD)
                assert isinstance(loc, StackLoc)
                self.mc.MOVSD_bx(loc.value, xmmtmp.value)
        self.mc.JMP_l(jmpadr)

    def _assemble_bootstrap_direct_call_64(self, arglocs, jmpadr, stackdepth):
        # XXX: Very similar to _emit_call_64

        src_locs = []
        dst_locs = []
        xmm_src_locs = []
        xmm_dst_locs = []
        get_from_stack = []

        # In reverse order for use with pop()
        unused_gpr = [r9, r8, ecx, edx, esi, edi]
        unused_xmm = [xmm7, xmm6, xmm5, xmm4, xmm3, xmm2, xmm1, xmm0]

        nonfloatlocs, floatlocs = arglocs
        adr_stackadjust = self._call_header()
        self._patch_stackadjust(adr_stackadjust, stackdepth)

        # The lists are padded with Nones
        assert len(nonfloatlocs) == len(floatlocs)

        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            if loc is not None:
                if len(unused_gpr) > 0:
                    src_locs.append(unused_gpr.pop())
                    dst_locs.append(loc)
                else:
                    get_from_stack.append((loc, False))

            floc = floatlocs[i]
            if floc is not None:
                if len(unused_xmm) > 0:
                    xmm_src_locs.append(unused_xmm.pop())
                    xmm_dst_locs.append(floc)
                else:
                    get_from_stack.append((floc, True))

        remap_frame_layout(self, src_locs, dst_locs, X86_64_SCRATCH_REG)
        remap_frame_layout(self, xmm_src_locs, xmm_dst_locs, X86_64_XMM_SCRATCH_REG)

        for i in range(len(get_from_stack)):
            loc, is_xmm = get_from_stack[i]
            if is_xmm:
                self.mc.MOVSD_xb(X86_64_XMM_SCRATCH_REG.value, (2 + i) * WORD)
                self.mc.MOVSD(loc, X86_64_XMM_SCRATCH_REG)
            else:
                self.mc.MOV_rb(X86_64_SCRATCH_REG.value, (2 + i) * WORD)
                # XXX: We're assuming that "loc" won't require regloc to
                # clobber the scratch register
                self.mc.MOV(loc, X86_64_SCRATCH_REG)

        finaljmp = self.mc.tell()
        self.mc.JMP(imm(jmpadr))

    def redirect_call_assembler(self, oldlooptoken, newlooptoken):
        # some minimal sanity checking
        oldnonfloatlocs, oldfloatlocs = oldlooptoken._x86_arglocs
        newnonfloatlocs, newfloatlocs = newlooptoken._x86_arglocs
        assert len(oldnonfloatlocs) == len(newnonfloatlocs)
        assert len(oldfloatlocs) == len(newfloatlocs)
        # we overwrite the instructions at the old _x86_direct_bootstrap_code
        # to start with a JMP to the new _x86_direct_bootstrap_code.
        # Ideally we should rather patch all existing CALLs, but well.
        oldadr = oldlooptoken._x86_direct_bootstrap_code
        target = newlooptoken._x86_direct_bootstrap_code
        mc = codebuf.InMemoryCodeBuilder(oldadr, oldadr + 16)
        mc.JMP(imm(target))
        mc.done()

    def _assemble_bootstrap_code(self, inputargs, arglocs):
        nonfloatlocs, floatlocs = arglocs
        adr_stackadjust = self._call_header()
        tmp = X86RegisterManager.all_regs[0]
        xmmtmp = X86XMMRegisterManager.all_regs[0]
        self.mc._mc.begin_reuse_scratch_register()
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            if loc is None:
                continue
            if isinstance(loc, RegLoc):
                target = loc
            else:
                target = tmp
            if inputargs[i].type == REF:
                # This uses XCHG to put zeroes in fail_boxes_ptr after
                # reading them
                self.mc.XOR(target, target)
                adr = self.fail_boxes_ptr.get_addr_for_num(i)
                self.mc.XCHG(target, heap(adr))
            else:
                adr = self.fail_boxes_int.get_addr_for_num(i)
                self.mc.MOV(target, heap(adr))
            if target is not loc:
                assert isinstance(loc, StackLoc)
                self.mc.MOV_br(loc.value, target.value)
        for i in range(len(floatlocs)):
            loc = floatlocs[i]
            if loc is None:
                continue
            adr = self.fail_boxes_float.get_addr_for_num(i)
            if isinstance(loc, RegLoc):
                self.mc.MOVSD(loc, heap(adr))
            else:
                self.mc.MOVSD(xmmtmp, heap(adr))
                assert isinstance(loc, StackLoc)
                self.mc.MOVSD_bx(loc.value, xmmtmp.value)
        self.mc._mc.end_reuse_scratch_register()
        return adr_stackadjust

    def dump(self, text):
        if not self.verbose:
            return
        _prev = Box._extended_display
        try:
            Box._extended_display = False
            print >> sys.stderr, ' 0x%x  %s' % (fixid(self.mc.tell()), text)
        finally:
            Box._extended_display = _prev

    # ------------------------------------------------------------

    def mov(self, from_loc, to_loc):
        if (isinstance(from_loc, RegLoc) and from_loc.is_xmm) or (isinstance(to_loc, RegLoc) and to_loc.is_xmm):
            self.mc.MOVSD(to_loc, from_loc)
        else:
            self.mc.MOV(to_loc, from_loc)

    regalloc_mov = mov # legacy interface

    def regalloc_push(self, loc):
        if isinstance(loc, RegLoc) and loc.is_xmm:
            self.mc.SUB_ri(esp.value, 2*WORD)
            self.mc.MOVSD_sx(0, loc.value)
        elif WORD == 4 and isinstance(loc, StackLoc) and loc.width == 8:
            # XXX evil trick
            self.mc.PUSH_b(get_ebp_ofs(loc.position))
            self.mc.PUSH_b(get_ebp_ofs(loc.position + 1))
        else:
            self.mc.PUSH(loc)

    def regalloc_pop(self, loc):
        if isinstance(loc, RegLoc) and loc.is_xmm:
            self.mc.MOVSD_xs(loc.value, 0)
            self.mc.ADD_ri(esp.value, 2*WORD)
        elif WORD == 4 and isinstance(loc, StackLoc) and loc.width == 8:
            # XXX evil trick
            self.mc.POP_b(get_ebp_ofs(loc.position + 1))
            self.mc.POP_b(get_ebp_ofs(loc.position))
        else:
            self.mc.POP(loc)

    def regalloc_perform(self, op, arglocs, resloc):
        genop_list[op.getopnum()](self, op, arglocs, resloc)

    def regalloc_perform_discard(self, op, arglocs):
        genop_discard_list[op.getopnum()](self, op, arglocs)

    def regalloc_perform_with_guard(self, op, guard_op, faillocs,
                                    arglocs, resloc, current_depths):
        faildescr = guard_op.getdescr()
        assert isinstance(faildescr, AbstractFailDescr)
        faildescr._x86_current_depths = current_depths
        failargs = guard_op.getfailargs()
        guard_opnum = guard_op.getopnum()
        guard_token = self.implement_guard_recovery(guard_opnum,
                                                    faildescr, failargs,
                                                    faillocs)
        if op is None:
            dispatch_opnum = guard_opnum
        else:
            dispatch_opnum = op.getopnum()
        res = genop_guard_list[dispatch_opnum](self, op, guard_op, guard_token,
                                               arglocs, resloc)
        faildescr._x86_adr_jump_offset = res

    def regalloc_perform_guard(self, guard_op, faillocs, arglocs, resloc,
                               current_depths):
        self.regalloc_perform_with_guard(None, guard_op, faillocs, arglocs,
                                         resloc, current_depths)

    def load_effective_addr(self, sizereg, baseofs, scale, result, frm=imm0):
        self.mc.LEA(result, addr_add(frm, sizereg, baseofs, scale))

    def _unaryop(asmop):
        def genop_unary(self, op, arglocs, resloc):
            getattr(self.mc, asmop)(arglocs[0])
        return genop_unary

    def _binaryop(asmop, can_swap=False):
        def genop_binary(self, op, arglocs, result_loc):
            getattr(self.mc, asmop)(arglocs[0], arglocs[1])
        return genop_binary

    def _cmpop(cond, rev_cond):
        def genop_cmp(self, op, arglocs, result_loc):
            rl = result_loc.lowest8bits()
            if isinstance(op.getarg(0), Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                self.mc.SET_ir(rx86.Conditions[rev_cond], rl.value)
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                self.mc.SET_ir(rx86.Conditions[cond], rl.value)
            self.mc.MOVZX8_rr(result_loc.value, rl.value)
        return genop_cmp

    def _cmpop_float(cond, is_ne=False):
        def genop_cmp(self, op, arglocs, result_loc):
            self.mc.UCOMISD(arglocs[0], arglocs[1])
            tmp1 = result_loc.lowest8bits()
            if IS_X86_32:
                tmp2 = result_loc.higher8bits()
            elif IS_X86_64:
                tmp2 = X86_64_SCRATCH_REG.lowest8bits()

            self.mc.SET_ir(rx86.Conditions[cond], tmp1.value)
            if is_ne:
                self.mc.SET_ir(rx86.Conditions['P'], tmp2.value)
                self.mc.OR8_rr(tmp1.value, tmp2.value)
            else:
                self.mc.SET_ir(rx86.Conditions['NP'], tmp2.value)
                self.mc.AND8_rr(tmp1.value, tmp2.value)
            self.mc.MOVZX8_rr(result_loc.value, tmp1.value)
        return genop_cmp

    def _cmpop_guard(cond, rev_cond, false_cond, false_rev_cond):
        def genop_cmp_guard(self, op, guard_op, guard_token, arglocs, result_loc):
            guard_opnum = guard_op.getopnum()
            if isinstance(op.getarg(0), Const):
                self.mc.CMP(arglocs[1], arglocs[0])
                if guard_opnum == rop.GUARD_FALSE:
                    return self.implement_guard(guard_token, rev_cond)
                else:
                    return self.implement_guard(guard_token, false_rev_cond)
            else:
                self.mc.CMP(arglocs[0], arglocs[1])
                if guard_opnum == rop.GUARD_FALSE:
                    return self.implement_guard(guard_token, cond)
                else:
                    return self.implement_guard(guard_token, false_cond)
        return genop_cmp_guard

    def _cmpop_guard_float(cond, false_cond, need_jp):
        def genop_cmp_guard_float(self, op, guard_op, guard_token, arglocs,
                                  result_loc):
            guard_opnum = guard_op.getopnum()
            self.mc.UCOMISD(arglocs[0], arglocs[1])
            # 16 is enough space for the rel8 jumps below and the rel32
            # jump in implement_guard
            self.mc.ensure_bytes_available(16 + guard_token.recovery_stub_size())
            if guard_opnum == rop.GUARD_FALSE:
                if need_jp:
                    self.mc.J_il8(rx86.Conditions['P'], 6)
                return self.implement_guard(guard_token, cond)
            else:
                if need_jp:
                    self.mc.J_il8(rx86.Conditions['P'], 2)
                    self.mc.J_il8(rx86.Conditions[cond], 5)
                    return self.implement_guard(guard_token)
                return self.implement_guard(guard_token, false_cond)
        return genop_cmp_guard_float

    def _emit_call(self, x, arglocs, start=0, tmp=eax):
        if IS_X86_64:
            return self._emit_call_64(x, arglocs, start)

        p = 0
        n = len(arglocs)
        for i in range(start, n):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                if loc.is_xmm:
                    self.mc.MOVSD_sx(p, loc.value)
                else:
                    self.mc.MOV_sr(p, loc.value)
            p += round_up_to_4(loc.width)
        p = 0
        for i in range(start, n):
            loc = arglocs[i]
            if not isinstance(loc, RegLoc):
                if loc.width == 8:
                    self.mc.MOVSD(xmm0, loc)
                    self.mc.MOVSD_sx(p, xmm0.value)
                else:
                    self.mc.MOV(tmp, loc)
                    self.mc.MOV_sr(p, tmp.value)
            p += round_up_to_4(loc.width)
        self._regalloc.reserve_param(p//WORD)
        # x is a location
        self.mc.CALL(x)
        self.mark_gc_roots()

    def _emit_call_64(self, x, arglocs, start=0):
        src_locs = []
        dst_locs = []
        xmm_src_locs = []
        xmm_dst_locs = []
        pass_on_stack = []

        # In reverse order for use with pop()
        unused_gpr = [r9, r8, ecx, edx, esi, edi]
        unused_xmm = [xmm7, xmm6, xmm5, xmm4, xmm3, xmm2, xmm1, xmm0]

        for i in range(start, len(arglocs)):
            loc = arglocs[i]
            # XXX: Should be much simplier to tell whether a location is a
            # float! It's so ugly because we have to "guard" the access to
            # .type with isinstance, since not all AssemblerLocation classes
            # are "typed"
            if ((isinstance(loc, RegLoc) and loc.is_xmm) or
                (isinstance(loc, StackLoc) and loc.type == FLOAT) or
                (isinstance(loc, ConstFloatLoc))):
                if len(unused_xmm) > 0:
                    xmm_src_locs.append(loc)
                    xmm_dst_locs.append(unused_xmm.pop())
                else:
                    pass_on_stack.append(loc)
            else:
                if len(unused_gpr) > 0:
                    src_locs.append(loc)
                    dst_locs.append(unused_gpr.pop())
                else:
                    pass_on_stack.append(loc)
        
        # Emit instructions to pass the stack arguments
        # XXX: Would be nice to let remap_frame_layout take care of this, but
        # we'd need to create something like StackLoc, but relative to esp,
        # and I don't know if it's worth it.
        for i in range(len(pass_on_stack)):
            loc = pass_on_stack[i]
            if not isinstance(loc, RegLoc):
                if isinstance(loc, StackLoc) and loc.type == FLOAT:
                    self.mc.MOVSD(X86_64_XMM_SCRATCH_REG, loc)
                    self.mc.MOVSD_sx(i*WORD, X86_64_XMM_SCRATCH_REG.value)
                else:
                    self.mc.MOV(X86_64_SCRATCH_REG, loc)
                    self.mc.MOV_sr(i*WORD, X86_64_SCRATCH_REG.value)
            else:
                # It's a register
                if loc.is_xmm:
                    self.mc.MOVSD_sx(i*WORD, loc.value)
                else:
                    self.mc.MOV_sr(i*WORD, loc.value)

        # Handle register arguments
        remap_frame_layout(self, src_locs, dst_locs, X86_64_SCRATCH_REG)
        remap_frame_layout(self, xmm_src_locs, xmm_dst_locs, X86_64_XMM_SCRATCH_REG)

        self._regalloc.reserve_param(len(pass_on_stack))
        self.mc.CALL(x)
        self.mark_gc_roots()

    def call(self, addr, args, res):
        self._emit_call(imm(addr), args)
        assert res is eax

    genop_int_neg = _unaryop("NEG")
    genop_int_invert = _unaryop("NOT")
    genop_int_add = _binaryop("ADD", True)
    genop_int_sub = _binaryop("SUB")
    genop_int_mul = _binaryop("IMUL", True)
    genop_int_and = _binaryop("AND", True)
    genop_int_or  = _binaryop("OR", True)
    genop_int_xor = _binaryop("XOR", True)
    genop_int_lshift = _binaryop("SHL")
    genop_int_rshift = _binaryop("SAR")
    genop_uint_rshift = _binaryop("SHR")
    genop_float_add = _binaryop("ADDSD", True)
    genop_float_sub = _binaryop('SUBSD')
    genop_float_mul = _binaryop('MULSD', True)
    genop_float_truediv = _binaryop('DIVSD')

    genop_int_lt = _cmpop("L", "G")
    genop_int_le = _cmpop("LE", "GE")
    genop_int_eq = _cmpop("E", "E")
    genop_int_ne = _cmpop("NE", "NE")
    genop_int_gt = _cmpop("G", "L")
    genop_int_ge = _cmpop("GE", "LE")
    genop_ptr_eq = genop_int_eq
    genop_ptr_ne = genop_int_ne

    genop_float_lt = _cmpop_float('B')
    genop_float_le = _cmpop_float('BE')
    genop_float_ne = _cmpop_float('NE', is_ne=True)
    genop_float_eq = _cmpop_float('E')
    genop_float_gt = _cmpop_float('A')
    genop_float_ge = _cmpop_float('AE')

    genop_uint_gt = _cmpop("A", "B")
    genop_uint_lt = _cmpop("B", "A")
    genop_uint_le = _cmpop("BE", "AE")
    genop_uint_ge = _cmpop("AE", "BE")

    genop_guard_int_lt = _cmpop_guard("L", "G", "GE", "LE")
    genop_guard_int_le = _cmpop_guard("LE", "GE", "G", "L")
    genop_guard_int_eq = _cmpop_guard("E", "E", "NE", "NE")
    genop_guard_int_ne = _cmpop_guard("NE", "NE", "E", "E")
    genop_guard_int_gt = _cmpop_guard("G", "L", "LE", "GE")
    genop_guard_int_ge = _cmpop_guard("GE", "LE", "L", "G")
    genop_guard_ptr_eq = genop_guard_int_eq
    genop_guard_ptr_ne = genop_guard_int_ne

    genop_guard_uint_gt = _cmpop_guard("A", "B", "BE", "AE")
    genop_guard_uint_lt = _cmpop_guard("B", "A", "AE", "BE")
    genop_guard_uint_le = _cmpop_guard("BE", "AE", "A", "B")
    genop_guard_uint_ge = _cmpop_guard("AE", "BE", "B", "A")

    genop_guard_float_lt = _cmpop_guard_float("B", "AE", True)
    genop_guard_float_le = _cmpop_guard_float("BE", "A", True)
    genop_guard_float_eq = _cmpop_guard_float("E", "NE", True)
    genop_guard_float_gt = _cmpop_guard_float("A", "BE", False)
    genop_guard_float_ge = _cmpop_guard_float("AE", "B", False)

    def genop_guard_float_ne(self, op, guard_op, guard_token, arglocs, result_loc):
        guard_opnum = guard_op.getopnum()
        self.mc.UCOMISD(arglocs[0], arglocs[1])
        # 16 is enough space for the rel8 jumps below and the rel32
        # jump in implement_guard
        self.mc.ensure_bytes_available(16 + guard_token.recovery_stub_size())
        if guard_opnum == rop.GUARD_TRUE:
            self.mc.J_il8(rx86.Conditions['P'], 6)
            return self.implement_guard(guard_token, 'E')
        else:
            self.mc.J_il8(rx86.Conditions['P'], 2)
            self.mc.J_il8(rx86.Conditions['E'], 5)
            return self.implement_guard(guard_token)

    def genop_float_neg(self, op, arglocs, resloc):
        # Following what gcc does: res = x ^ 0x8000000000000000
        self.mc.XORPD(arglocs[0], heap(self.float_const_neg_addr))

    def genop_float_abs(self, op, arglocs, resloc):
        # Following what gcc does: res = x & 0x7FFFFFFFFFFFFFFF
        self.mc.ANDPD(arglocs[0], heap(self.float_const_abs_addr))

    def genop_cast_float_to_int(self, op, arglocs, resloc):
        self.mc.CVTTSD2SI(resloc, arglocs[0])

    def genop_cast_int_to_float(self, op, arglocs, resloc):
        self.mc.CVTSI2SD(resloc, arglocs[0])

    def genop_guard_int_is_true(self, op, guard_op, guard_token, arglocs, resloc):
        guard_opnum = guard_op.getopnum()
        self.mc.CMP(arglocs[0], imm0)
        if guard_opnum == rop.GUARD_TRUE:
            return self.implement_guard(guard_token, 'Z')
        else:
            return self.implement_guard(guard_token, 'NZ')

    def genop_int_is_true(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm0)
        rl = resloc.lowest8bits()
        self.mc.SET_ir(rx86.Conditions['NE'], rl.value)
        self.mc.MOVZX8(resloc, rl)

    def genop_guard_int_is_zero(self, op, guard_op, guard_token, arglocs, resloc):
        guard_opnum = guard_op.getopnum()
        self.mc.CMP(arglocs[0], imm0)
        if guard_opnum == rop.GUARD_TRUE:
            return self.implement_guard(guard_token, 'NZ')
        else:
            return self.implement_guard(guard_token, 'Z')

    def genop_int_is_zero(self, op, arglocs, resloc):
        self.mc.CMP(arglocs[0], imm0)
        rl = resloc.lowest8bits()
        self.mc.SET_ir(rx86.Conditions['E'], rl.value)
        self.mc.MOVZX8(resloc, rl)

    def genop_same_as(self, op, arglocs, resloc):
        self.mov(arglocs[0], resloc)
    #genop_cast_ptr_to_int = genop_same_as

    def genop_int_mod(self, op, arglocs, resloc):
        if IS_X86_32:
            self.mc.CDQ()
        elif IS_X86_64:
            self.mc.CQO()

        self.mc.IDIV_r(ecx.value)

    genop_int_floordiv = genop_int_mod

    def genop_uint_floordiv(self, op, arglocs, resloc):
        self.mc.XOR_rr(edx.value, edx.value)
        self.mc.DIV_r(ecx.value)

    def genop_new_with_vtable(self, op, arglocs, result_loc):
        assert result_loc is eax
        loc_vtable = arglocs[-1]
        assert isinstance(loc_vtable, ImmedLoc)
        arglocs = arglocs[:-1]
        self.call(self.malloc_func_addr, arglocs, eax)
        # xxx ignore NULL returns for now
        self.set_vtable(eax, loc_vtable)

    def set_vtable(self, loc, loc_vtable):
        if self.cpu.vtable_offset is not None:
            assert isinstance(loc, RegLoc)
            assert isinstance(loc_vtable, ImmedLoc)
            self.mc.MOV(mem(loc, self.cpu.vtable_offset), loc_vtable)

    # XXX genop_new is abused for all varsized mallocs with Boehm, for now
    # (instead of genop_new_array, genop_newstr, genop_newunicode)
    def genop_new(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_func_addr, arglocs, eax)

    def genop_new_array(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_array_func_addr, arglocs, eax)

    def genop_newstr(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_str_func_addr, arglocs, eax)

    def genop_newunicode(self, op, arglocs, result_loc):
        assert result_loc is eax
        self.call(self.malloc_unicode_func_addr, arglocs, eax)

    # ----------

    def load_from_mem(self, resloc, source_addr, size_loc, sign_loc):
        assert isinstance(resloc, RegLoc)
        size = size_loc.value
        sign = sign_loc.value
        if resloc.is_xmm:
            self.mc.MOVSD(resloc, source_addr)
        elif size == WORD:
            self.mc.MOV(resloc, source_addr)
        elif size == 1:
            if sign:
                self.mc.MOVSX8(resloc, source_addr)
            else:
                self.mc.MOVZX8(resloc, source_addr)
        elif size == 2:
            if sign:
                self.mc.MOVSX16(resloc, source_addr)
            else:
                self.mc.MOVZX16(resloc, source_addr)
        elif IS_X86_64 and size == 4:
            if sign:
                self.mc.MOVSX32(resloc, source_addr)
            else:
                self.mc.MOV32(resloc, source_addr)    # zero-extending
        else:
            not_implemented("load_from_mem size = %d" % size)

    def save_into_mem(self, dest_addr, value_loc, size_loc):
        size = size_loc.value
        if isinstance(value_loc, RegLoc) and value_loc.is_xmm:
            self.mc.MOVSD(dest_addr, value_loc)
        elif size == 1:
            self.mc.MOV8(dest_addr, value_loc.lowest8bits())
        elif size == 2:
            self.mc.MOV16(dest_addr, value_loc)
        elif size == 4:
            self.mc.MOV32(dest_addr, value_loc)
        elif IS_X86_64 and size == 8:
            self.mc.MOV(dest_addr, value_loc)
        else:
            not_implemented("save_into_mem size = %d" % size)

    def genop_getfield_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc, sign_loc = arglocs
        assert isinstance(size_loc, ImmedLoc)
        source_addr = AddressLoc(base_loc, ofs_loc)
        self.load_from_mem(resloc, source_addr, size_loc, sign_loc)

    genop_getfield_raw = genop_getfield_gc
    genop_getfield_raw_pure = genop_getfield_gc
    genop_getfield_gc_pure = genop_getfield_gc

    def genop_getarrayitem_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc, size_loc, ofs, sign_loc = arglocs
        assert isinstance(ofs, ImmedLoc)
        assert isinstance(size_loc, ImmedLoc)
        scale = _get_scale(size_loc.value)
        src_addr = addr_add(base_loc, ofs_loc, ofs.value, scale)
        self.load_from_mem(resloc, src_addr, size_loc, sign_loc)

    genop_getarrayitem_gc_pure = genop_getarrayitem_gc
    genop_getarrayitem_raw = genop_getarrayitem_gc

    def genop_discard_setfield_gc(self, op, arglocs):
        base_loc, ofs_loc, size_loc, value_loc = arglocs
        assert isinstance(size_loc, ImmedLoc)
        dest_addr = AddressLoc(base_loc, ofs_loc)
        self.save_into_mem(dest_addr, value_loc, size_loc)

    def genop_discard_setarrayitem_gc(self, op, arglocs):
        base_loc, ofs_loc, value_loc, size_loc, baseofs = arglocs
        assert isinstance(baseofs, ImmedLoc)
        assert isinstance(size_loc, ImmedLoc)
        scale = _get_scale(size_loc.value)
        dest_addr = AddressLoc(base_loc, ofs_loc, scale, baseofs.value)
        self.save_into_mem(dest_addr, value_loc, size_loc)

    def genop_discard_strsetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                              self.cpu.translate_support_code)
        assert itemsize == 1
        dest_addr = AddressLoc(base_loc, ofs_loc, 0, basesize)
        self.mc.MOV8(dest_addr, val_loc.lowest8bits())

    def genop_discard_unicodesetitem(self, op, arglocs):
        base_loc, ofs_loc, val_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                              self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV32(AddressLoc(base_loc, ofs_loc, 2, basesize), val_loc)
        elif itemsize == 2:
            self.mc.MOV16(AddressLoc(base_loc, ofs_loc, 1, basesize), val_loc)
        else:
            assert 0, itemsize

    genop_discard_setfield_raw = genop_discard_setfield_gc
    genop_discard_setarrayitem_raw = genop_discard_setarrayitem_gc

    def genop_strlen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_unicodelen(self, op, arglocs, resloc):
        base_loc = arglocs[0]
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_length))

    def genop_arraylen_gc(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        assert isinstance(ofs_loc, ImmedLoc)
        self.mc.MOV(resloc, addr_add_const(base_loc, ofs_loc.value))

    def genop_strgetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.STR,
                                             self.cpu.translate_support_code)
        assert itemsize == 1
        self.mc.MOVZX8(resloc, AddressLoc(base_loc, ofs_loc, 0, basesize))

    def genop_unicodegetitem(self, op, arglocs, resloc):
        base_loc, ofs_loc = arglocs
        basesize, itemsize, ofs_length = symbolic.get_array_token(rstr.UNICODE,
                                             self.cpu.translate_support_code)
        if itemsize == 4:
            self.mc.MOV32(resloc, AddressLoc(base_loc, ofs_loc, 2, basesize))
        elif itemsize == 2:
            self.mc.MOVZX16(resloc, AddressLoc(base_loc, ofs_loc, 1, basesize))
        else:
            assert 0, itemsize

    def genop_guard_guard_true(self, ign_1, guard_op, guard_token, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        return self.implement_guard(guard_token, 'Z')
    genop_guard_guard_nonnull = genop_guard_guard_true

    def genop_guard_guard_no_exception(self, ign_1, guard_op, guard_token,
                                       locs, ign_2):
        self.mc.CMP(heap(self.cpu.pos_exception()), imm0)
        return self.implement_guard(guard_token, 'NZ')

    def genop_guard_guard_exception(self, ign_1, guard_op, guard_token,
                                    locs, resloc):
        loc = locs[0]
        loc1 = locs[1]
        self.mc.MOV(loc1, heap(self.cpu.pos_exception()))
        self.mc.CMP(loc1, loc)
        addr = self.implement_guard(guard_token, 'NE')
        if resloc is not None:
            self.mc.MOV(resloc, heap(self.cpu.pos_exc_value()))
        self.mc.MOV(heap(self.cpu.pos_exception()), imm0)
        self.mc.MOV(heap(self.cpu.pos_exc_value()), imm0)
        return addr

    def _gen_guard_overflow(self, guard_op, guard_token):
        guard_opnum = guard_op.getopnum()
        if guard_opnum == rop.GUARD_NO_OVERFLOW:
            return self.implement_guard(guard_token, 'O')
        elif guard_opnum == rop.GUARD_OVERFLOW:
            return self.implement_guard(guard_token, 'NO')
        else:
            not_implemented("int_xxx_ovf followed by %s" %
                            guard_op.getopname())

    def genop_guard_int_add_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.genop_int_add(op, arglocs, result_loc)
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_int_sub_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.genop_int_sub(op, arglocs, result_loc)
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_int_mul_ovf(self, op, guard_op, guard_token, arglocs, result_loc):
        self.genop_int_mul(op, arglocs, result_loc)
        return self._gen_guard_overflow(guard_op, guard_token)

    def genop_guard_guard_false(self, ign_1, guard_op, guard_token, locs, ign_2):
        loc = locs[0]
        self.mc.TEST(loc, loc)
        return self.implement_guard(guard_token, 'NZ')
    genop_guard_guard_isnull = genop_guard_guard_false

    def genop_guard_guard_value(self, ign_1, guard_op, guard_token, locs, ign_2):
        if guard_op.getarg(0).type == FLOAT:
            assert guard_op.getarg(1).type == FLOAT
            self.mc.UCOMISD(locs[0], locs[1])
        else:
            self.mc.CMP(locs[0], locs[1])
        return self.implement_guard(guard_token, 'NE')

    def _cmp_guard_class(self, locs):
        offset = self.cpu.vtable_offset
        if offset is not None:
            self.mc.CMP(mem(locs[0], offset), locs[1])
        else:
            # XXX hard-coded assumption: to go from an object to its class
            # we use the following algorithm:
            #   - read the typeid from mem(locs[0]), i.e. at offset 0
            #   - keep the lower 16 bits read there
            #   - multiply by 4 and use it as an offset in type_info_group
            #   - add 16 bytes, to go past the TYPE_INFO structure
            loc = locs[1]
            assert isinstance(loc, ImmedLoc)
            classptr = loc.value
            # here, we have to go back from 'classptr' to the value expected
            # from reading the 16 bits in the object header
            from pypy.rpython.memory.gctypelayout import GCData
            sizeof_ti = rffi.sizeof(GCData.TYPE_INFO)
            type_info_group = llop.gc_get_type_info_group(llmemory.Address)
            type_info_group = rffi.cast(lltype.Signed, type_info_group)
            expected_typeid = classptr - sizeof_ti - type_info_group
            if IS_X86_32:
                expected_typeid >>= 2
                self.mc.CMP16(mem(locs[0], 0), ImmedLoc(expected_typeid))
            elif IS_X86_64:
                self.mc.CMP32_mi((locs[0].value, 0), expected_typeid)

    def genop_guard_guard_class(self, ign_1, guard_op, guard_token, locs, ign_2):
        self.mc.ensure_bytes_available(256)
        self._cmp_guard_class(locs)
        return self.implement_guard(guard_token, 'NE')

    def genop_guard_guard_nonnull_class(self, ign_1, guard_op,
                                        guard_token, locs, ign_2):
        self.mc.ensure_bytes_available(256)
        self.mc.CMP(locs[0], imm1)
        # Patched below
        self.mc.J_il8(rx86.Conditions['B'], 0)
        jb_location = self.mc.get_relative_pos()
        self._cmp_guard_class(locs)
        # patch the JB above
        offset = self.mc.get_relative_pos() - jb_location
        assert 0 < offset <= 127
        self.mc.overwrite(jb_location-1, [chr(offset)])
        #
        return self.implement_guard(guard_token, 'NE')

    def implement_guard_recovery(self, guard_opnum, faildescr, failargs,
                                                               fail_locs):
        exc = (guard_opnum == rop.GUARD_EXCEPTION or
               guard_opnum == rop.GUARD_NO_EXCEPTION or
               guard_opnum == rop.GUARD_NOT_FORCED)
        desc_bytes = self.failure_recovery_description(failargs, fail_locs)
        return GuardToken(faildescr, failargs, fail_locs, exc, desc_bytes)

    def generate_quick_failure(self, mc, faildescr, failargs, fail_locs, exc, desc_bytes):
        """Generate the initial code for handling a failure.  We try to
        keep it as compact as possible.  The idea is that this code is
        executed at most once (and very often, zero times); when
        executed, it generates a more complete piece of code which can
        really handle recovery from this particular failure.
        """
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        addr = mc.tell()
        withfloats = False
        for box in failargs:
            if box is not None and box.type == FLOAT:
                withfloats = True
                break
        mc.CALL(imm(self.failure_recovery_code[exc + 2 * withfloats]))
        # write tight data that describes the failure recovery
        faildescr._x86_failure_recovery_bytecode = mc.tell()
        for byte in desc_bytes:
            mc.writechr(ord(byte))
        # write the fail_index too
        mc.writeimm32(fail_index)
        # for testing the decoding, write a final byte 0xCC
        if not we_are_translated():
            mc.writechr(0xCC)
            faildescr._x86_debug_faillocs = [loc for loc in fail_locs
                                                 if loc is not None]

        # Make sure the recovery stub is at least 16 bytes long (for the
        # case where we overwrite the recovery stub with a 64-bit absolute
        # jump)
        while mc.tell() - addr < 16:
            mc.writechr(0x00)
        return addr

    DESCR_REF       = 0x00
    DESCR_INT       = 0x01
    DESCR_FLOAT     = 0x02
    DESCR_SPECIAL   = 0x03
    # XXX: 4*8 works on i386, should we optimize for that case?
    CODE_FROMSTACK  = 4*16
    CODE_STOP       = 0 | DESCR_SPECIAL
    CODE_HOLE       = 4 | DESCR_SPECIAL

    def failure_recovery_description(self, failargs, locs):
        desc_bytes = []
        for i in range(len(failargs)):
            arg = failargs[i]
            if arg is not None:
                if arg.type == REF:
                    kind = self.DESCR_REF
                elif arg.type == INT:
                    kind = self.DESCR_INT
                elif arg.type == FLOAT:
                    kind = self.DESCR_FLOAT
                else:
                    raise AssertionError("bogus kind")
                loc = locs[i]
                if isinstance(loc, StackLoc):
                    n = self.CODE_FROMSTACK//4 + loc.position
                else:
                    assert isinstance(loc, RegLoc)
                    n = loc.value
                n = kind + 4*n
                while n > 0x7F:
                    desc_bytes.append(chr((n & 0x7F) | 0x80))
                    n >>= 7
            else:
                n = self.CODE_HOLE
            desc_bytes.append(chr(n))
        desc_bytes.append(chr(self.CODE_STOP))
        # assert that the fail_boxes lists are big enough
        assert len(failargs) <= self.fail_boxes_int.SIZE
        return desc_bytes

    def write_failure_recovery_description(self, mc, failargs, locs):
        for byte in self.failure_recovery_description(failargs, locs):
            mc.writechr(ord(byte))

    def rebuild_faillocs_from_descr(self, bytecode):
        from pypy.jit.backend.x86.regalloc import X86FrameManager
        descr_to_box_type = [REF, INT, FLOAT]
        bytecode = rffi.cast(rffi.UCHARP, bytecode)
        arglocs = []
        while 1:
            # decode the next instruction from the bytecode
            code = rffi.cast(lltype.Signed, bytecode[0])
            bytecode = rffi.ptradd(bytecode, 1)
            if code >= self.CODE_FROMSTACK:
                # 'code' identifies a stack location
                if code > 0x7F:
                    shift = 7
                    code &= 0x7F
                    while True:
                        nextcode = rffi.cast(lltype.Signed, bytecode[0])
                        bytecode = rffi.ptradd(bytecode, 1)
                        code |= (nextcode & 0x7F) << shift
                        shift += 7
                        if nextcode <= 0x7F:
                            break
                kind = code & 3
                code = (code - self.CODE_FROMSTACK) >> 2
                if kind == self.DESCR_FLOAT:
                    size = 2
                else:
                    size = 1
                loc = X86FrameManager.frame_pos(code, descr_to_box_type[kind])
            elif code == self.CODE_STOP:
                break
            elif code == self.CODE_HOLE:
                continue
            else:
                # 'code' identifies a register
                kind = code & 3
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    loc = regloc.XMMREGLOCS[code]
                else:
                    loc = regloc.REGLOCS[code]
            arglocs.append(loc)
        return arglocs[:]

    @rgc.no_collect
    def grab_frame_values(self, bytecode, frame_addr, allregisters):
        # no malloc allowed here!!
        self.fail_ebp = allregisters[16 + ebp.value]
        num = 0
        value_hi = 0
        while 1:
            # decode the next instruction from the bytecode
            code = rffi.cast(lltype.Signed, bytecode[0])
            bytecode = rffi.ptradd(bytecode, 1)
            if code >= self.CODE_FROMSTACK:
                if code > 0x7F:
                    shift = 7
                    code &= 0x7F
                    while True:
                        nextcode = rffi.cast(lltype.Signed, bytecode[0])
                        bytecode = rffi.ptradd(bytecode, 1)
                        code |= (nextcode & 0x7F) << shift
                        shift += 7
                        if nextcode <= 0x7F:
                            break
                # load the value from the stack
                kind = code & 3
                code = (code - self.CODE_FROMSTACK) >> 2
                stackloc = frame_addr + get_ebp_ofs(code)
                value = rffi.cast(rffi.LONGP, stackloc)[0]
                if kind == self.DESCR_FLOAT and WORD == 4:
                    value_hi = value
                    value = rffi.cast(rffi.LONGP, stackloc - 4)[0]
            else:
                # 'code' identifies a register: load its value
                kind = code & 3
                if kind == self.DESCR_SPECIAL:
                    if code == self.CODE_HOLE:
                        num += 1
                        continue
                    assert code == self.CODE_STOP
                    break
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    if WORD == 4:
                        value = allregisters[2*code]
                        value_hi = allregisters[2*code + 1]
                    else:
                        value = allregisters[code]
                else:
                    value = allregisters[16 + code]

            # store the loaded value into fail_boxes_<type>
            if kind == self.DESCR_INT:
                tgt = self.fail_boxes_int.get_addr_for_num(num)
            elif kind == self.DESCR_REF:
                tgt = self.fail_boxes_ptr.get_addr_for_num(num)
            elif kind == self.DESCR_FLOAT:
                tgt = self.fail_boxes_float.get_addr_for_num(num)
                if WORD == 4:
                    rffi.cast(rffi.LONGP, tgt)[1] = value_hi
            else:
                assert 0, "bogus kind"
            rffi.cast(rffi.LONGP, tgt)[0] = value
            num += 1
        #
        if not we_are_translated():
            assert bytecode[4] == 0xCC
        self.fail_boxes_count = num
        fail_index = rffi.cast(rffi.INTP, bytecode)[0]
        fail_index = rffi.cast(lltype.Signed, fail_index)
        return fail_index

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(registers):
            # 'registers' is a pointer to a structure containing the
            # original value of the registers, optionally the original
            # value of XMM registers, and finally a reference to the
            # recovery bytecode.  See _build_failure_recovery() for details.
            stack_at_ebp = registers[ebp.value]
            bytecode = rffi.cast(rffi.UCHARP, registers[self.cpu.NUM_REGS])
            allregisters = rffi.ptradd(registers, -16)
            return self.grab_frame_values(bytecode, stack_at_ebp, allregisters)

        self.failure_recovery_func = failure_recovery_func
        self.failure_recovery_code = [0, 0, 0, 0]

    _FAILURE_RECOVERY_FUNC = lltype.Ptr(lltype.FuncType([rffi.LONGP],
                                                        lltype.Signed))

    def _build_failure_recovery(self, exc, withfloats=False):
        failure_recovery_func = llhelper(self._FAILURE_RECOVERY_FUNC,
                                         self.failure_recovery_func)
        failure_recovery_func = rffi.cast(lltype.Signed,
                                          failure_recovery_func)
        mc = self.mc._mc
        # Assume that we are called at the beginning, when there is no risk
        # that 'mc' runs out of space.  Checked by asserts in mc.write().
        recovery_addr = mc.tell()

        # Push all general purpose registers
        for gpr in range(self.cpu.NUM_REGS-1, -1, -1):
            mc.PUSH_r(gpr)

        # ebx/rbx is callee-save in both i386 and x86-64
        mc.MOV_rr(ebx.value, esp.value)

        if withfloats:
            # Push all float registers
            mc.SUB_ri(esp.value, self.cpu.NUM_REGS*8)
            for i in range(self.cpu.NUM_REGS):
                mc.MOVSD_sx(8*i, i)

        # we call a provided function that will
        # - call our on_leave_jitted_hook which will mark
        #   the fail_boxes_ptr array as pointing to young objects to
        #   avoid unwarranted freeing
        # - optionally save exception depending on the flag
        addr = self.cpu.get_on_leave_jitted_int(save_exception=exc)
        mc.CALL(imm(addr))

        # the following call saves all values from the stack and from
        # registers to the right 'fail_boxes_<type>' location.
        # Note that the registers are saved so far in esi[0] to esi[7],
        # as pushed above, plus optionally in esi[-16] to esi[-1] for
        # the XMM registers.  Moreover, esi[8] is a pointer to the recovery
        # bytecode, pushed just before by the CALL instruction written by
        # generate_quick_failure().  XXX misaligned stack in the call, but
        # it's ok because failure_recovery_func is not calling anything more

        # XXX
        if IS_X86_32:
            mc.PUSH_r(ebx.value)
        elif IS_X86_64:
            mc.MOV_rr(edi.value, ebx.value)
            # XXX: Correct to only align the stack on 64-bit?
            mc.AND_ri(esp.value, -16)
        else:
            raise AssertionError("Shouldn't happen")

        mc.CALL(imm(failure_recovery_func))
        # returns in eax the fail_index

        # now we return from the complete frame, which starts from
        # _assemble_bootstrap_code().  The LEA in _call_footer below throws
        # away most of the frame, including all the PUSHes that we did just
        # above.

        self._call_footer()
        self.mc.done()
        self.failure_recovery_code[exc + 2 * withfloats] = recovery_addr

    def generate_failure(self, fail_index, locs, exc, locs_are_ref):
        self.mc._mc.begin_reuse_scratch_register()
        for i in range(len(locs)):
            loc = locs[i]
            if isinstance(loc, RegLoc):
                if loc.is_xmm:
                    adr = self.fail_boxes_float.get_addr_for_num(i)
                    self.mc.MOVSD(heap(adr), loc)
                else:
                    if locs_are_ref[i]:
                        adr = self.fail_boxes_ptr.get_addr_for_num(i)
                    else:
                        adr = self.fail_boxes_int.get_addr_for_num(i)
                    self.mc.MOV(heap(adr), loc)
        for i in range(len(locs)):
            loc = locs[i]
            if not isinstance(loc, RegLoc):
                if isinstance(loc, StackLoc) and loc.type == FLOAT:
                    self.mc.MOVSD_xb(xmm0.value, loc.value)
                    adr = self.fail_boxes_float.get_addr_for_num(i)
                    self.mc.MOVSD(heap(adr), xmm0)
                else:
                    if locs_are_ref[i]:
                        adr = self.fail_boxes_ptr.get_addr_for_num(i)
                    else:
                        adr = self.fail_boxes_int.get_addr_for_num(i)
                    self.mc.MOV(eax, loc)
                    self.mc.MOV(heap(adr), eax)
        self.mc._mc.end_reuse_scratch_register()

        # we call a provided function that will
        # - call our on_leave_jitted_hook which will mark
        #   the fail_boxes_ptr array as pointing to young objects to
        #   avoid unwarranted freeing
        # - optionally save exception depending on the flag
        addr = self.cpu.get_on_leave_jitted_int(save_exception=exc)
        self.mc.CALL(imm(addr))

        self.mc.MOV_ri(eax.value, fail_index)

        # exit function
        self._call_footer()

    def implement_guard(self, guard_token, condition=None):
        self.mc.reserve_bytes(guard_token.recovery_stub_size())
        self.pending_guard_tokens.append(guard_token)
        # XXX: These jumps are patched later, the self.mc.tell() are just
        # dummy values
        if condition:
            self.mc.J_il(rx86.Conditions[condition], self.mc.tell())
        else:
            self.mc.JMP_l(self.mc.tell())
        return self.mc.tell() - 4

    def genop_call(self, op, arglocs, resloc):
        sizeloc = arglocs[0]
        assert isinstance(sizeloc, ImmedLoc)
        size = sizeloc.value
        signloc = arglocs[1]

        if isinstance(op.getarg(0), Const):
            x = imm(op.getarg(0).getint())
        else:
            x = arglocs[2]
        if x is eax:
            tmp = ecx
        else:
            tmp = eax
        
        self._emit_call(x, arglocs, 3, tmp=tmp)

        if IS_X86_32 and isinstance(resloc, StackLoc) and resloc.width == 8:
            self.mc.FSTP_b(resloc.value)   # float return
        elif size == WORD:
            assert resloc is eax or resloc is xmm0    # a full word
        elif size == 0:
            pass    # void return
        else:
            # use the code in load_from_mem to do the zero- or sign-extension
            assert resloc is eax
            if size == 1:
                srcloc = eax.lowest8bits()
            else:
                srcloc = eax
            self.load_from_mem(eax, srcloc, sizeloc, signloc)

    def genop_guard_call_may_force(self, op, guard_op, guard_token,
                                   arglocs, result_loc):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.mc.MOV_bi(FORCE_INDEX_OFS, fail_index)
        self.genop_call(op, arglocs, result_loc)
        self.mc.CMP_bi(FORCE_INDEX_OFS, 0)
        return self.implement_guard(guard_token, 'L')

    def genop_guard_call_assembler(self, op, guard_op, guard_token,
                                   arglocs, result_loc):
        faildescr = guard_op.getdescr()
        fail_index = self.cpu.get_fail_descr_number(faildescr)
        self.mc.MOV_bi(FORCE_INDEX_OFS, fail_index)
        descr = op.getdescr()
        assert isinstance(descr, LoopToken)
        assert len(arglocs) - 2 == len(descr._x86_arglocs[0])
        #
        # Write a call to the direct_bootstrap_code of the target assembler
        self._emit_call(imm(descr._x86_direct_bootstrap_code), arglocs, 2,
                        tmp=eax)
        self.mc.ensure_bytes_available(256)
        if op.result is None:
            assert result_loc is None
            value = self.cpu.done_with_this_frame_void_v
        else:
            kind = op.result.type
            if kind == INT:
                assert result_loc is eax
                value = self.cpu.done_with_this_frame_int_v
            elif kind == REF:
                assert result_loc is eax
                value = self.cpu.done_with_this_frame_ref_v
            elif kind == FLOAT:
                value = self.cpu.done_with_this_frame_float_v
            else:
                raise AssertionError(kind)
        self.mc.CMP_ri(eax.value, value)
        # patched later
        self.mc.J_il8(rx86.Conditions['E'], 0) # goto B if we get 'done_with_this_frame'
        je_location = self.mc.get_relative_pos()
        #
        # Path A: use assembler_helper_adr
        jd = descr.outermost_jitdriver_sd
        assert jd is not None
        asm_helper_adr = self.cpu.cast_adr_to_int(jd.assembler_helper_adr)
        self._emit_call(imm(asm_helper_adr), [eax, arglocs[1]], 0,
                        tmp=ecx)
        if IS_X86_32 and isinstance(result_loc, StackLoc) and result_loc.type == FLOAT:
            self.mc.FSTP_b(result_loc.value)
        #else: result_loc is already either eax or None, checked below
        self.mc.JMP_l8(0) # jump to done, patched later
        jmp_location = self.mc.get_relative_pos()
        #
        # Path B: fast path.  Must load the return value, and reset the token
        offset = jmp_location - je_location
        assert 0 < offset <= 127
        self.mc.overwrite(je_location - 1, [chr(offset)])
        #
        # Reset the vable token --- XXX really too much special logic here:-(
        if jd.index_of_virtualizable >= 0:
            from pypy.jit.backend.llsupport.descr import BaseFieldDescr
            fielddescr = jd.vable_token_descr
            assert isinstance(fielddescr, BaseFieldDescr)
            ofs = fielddescr.offset
            self.mc.MOV(eax, arglocs[1])
            self.mc.MOV_mi((eax.value, ofs), 0)
            # in the line above, TOKEN_NONE = 0
        #
        if op.result is not None:
            # load the return value from fail_boxes_xxx[0]
            kind = op.result.type
            if kind == FLOAT:
                xmmtmp = X86XMMRegisterManager.all_regs[0]
                adr = self.fail_boxes_float.get_addr_for_num(0)
                self.mc.MOVSD(xmmtmp, heap(adr))
                self.mc.MOVSD(result_loc, xmmtmp)
            else:
                assert result_loc is eax
                if kind == INT:
                    adr = self.fail_boxes_int.get_addr_for_num(0)
                    self.mc.MOV(eax, heap(adr))
                elif kind == REF:
                    adr = self.fail_boxes_ptr.get_addr_for_num(0)
                    self.mc.XOR_rr(eax.value, eax.value)
                    self.mc.XCHG(eax, heap(adr))
                else:
                    raise AssertionError(kind)
        #
        # Here we join Path A and Path B again
        offset = self.mc.get_relative_pos() - jmp_location
        assert 0 <= offset <= 127
        self.mc.overwrite(jmp_location - 1, [chr(offset)])
        self.mc.CMP_bi(FORCE_INDEX_OFS, 0)
        return self.implement_guard(guard_token, 'L')

    def genop_discard_cond_call_gc_wb(self, op, arglocs):
        # use 'mc._mc' directly instead of 'mc', to avoid
        # bad surprizes if the code buffer is mostly full
        descr = op.getdescr()
        if we_are_translated():
            cls = self.cpu.gc_ll_descr.has_write_barrier_class()
            assert cls is not None and isinstance(descr, cls)
        loc_base = arglocs[0]
        self.mc.ensure_bytes_available(256)
        self.mc.TEST8_mi((loc_base.value, descr.jit_wb_if_flag_byteofs),
                descr.jit_wb_if_flag_singlebyte)
        self.mc.J_il8(rx86.Conditions['Z'], 0) # patched later
        jz_location = self.mc.get_relative_pos()
        # the following is supposed to be the slow path, so whenever possible
        # we choose the most compact encoding over the most efficient one.
        # XXX improve a bit, particularly for IS_X86_64.
        for i in range(len(arglocs)-1, -1, -1):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                self.mc.PUSH_r(loc.value)
            else:
                if IS_X86_64:
                    self.mc.MOV_ri(X86_64_SCRATCH_REG.value, loc.getint())
                    self.mc.PUSH_r(X86_64_SCRATCH_REG.value)
                else:
                    self.mc.PUSH_i32(loc.getint())
        
        if IS_X86_64:
            # We clobber these registers to pass the arguments, but that's
            # okay, because consider_cond_call_gc_wb makes sure that any
            # caller-save registers with values in them are present in arglocs,
            # so they are saved on the stack above and restored below 
            self.mc.MOV_rs(edi.value, 0)
            self.mc.MOV_rs(esi.value, 8)

        # misaligned stack in the call, but it's ok because the write barrier
        # is not going to call anything more.  Also, this assumes that the
        # write barrier does not touch the xmm registers.
        self.mc.CALL(imm(descr.get_write_barrier_fn(self.cpu)))
        for i in range(len(arglocs)):
            loc = arglocs[i]
            if isinstance(loc, RegLoc):
                self.mc.POP_r(loc.value)
            else:
                self.mc.ADD_ri(esp.value, WORD)   # ignore the pushed constant
        # patch the JZ above
        offset = self.mc.get_relative_pos() - jz_location
        assert 0 < offset <= 127
        self.mc.overwrite(jz_location-1, [chr(offset)])

    def genop_force_token(self, op, arglocs, resloc):
        # RegAlloc.consider_force_token ensures this:
        assert isinstance(resloc, RegLoc)
        self.mc.LEA_rb(resloc.value, FORCE_INDEX_OFS)

    def not_implemented_op_discard(self, op, arglocs):
        not_implemented("not implemented operation: %s" % op.getopname())

    def not_implemented_op(self, op, arglocs, resloc):
        not_implemented("not implemented operation with res: %s" %
                        op.getopname())

    def not_implemented_op_guard(self, op, guard_op,
                                 failaddr, arglocs, resloc):
        not_implemented("not implemented operation (guard): %s" %
                        op.getopname())

    def mark_gc_roots(self):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            mark = self._regalloc.get_mark_gc_roots(gcrootmap)
            gcrootmap.put(rffi.cast(llmemory.Address, self.mc.tell()), mark)

    def target_arglocs(self, loop_token):
        return loop_token._x86_arglocs

    def closing_jump(self, loop_token):
        self.mc.JMP(imm(loop_token._x86_loop_code))

    def malloc_cond_fixedsize(self, nursery_free_adr, nursery_top_adr,
                              size, tid):
        self.mc.ensure_bytes_available(256)
        self.mc.MOV(eax, heap(nursery_free_adr))
        self.mc.LEA_rm(edx.value, (eax.value, size))
        self.mc.CMP(edx, heap(nursery_top_adr))
        self.mc.J_il8(rx86.Conditions['NA'], 0) # patched later
        jmp_adr = self.mc.get_relative_pos()

        # See comments in _build_malloc_fixedsize_slowpath for the
        # details of the two helper functions that we are calling below.
        # First, we need to call two of them and not just one because we
        # need to have a mark_gc_roots() in between.  Then the calling
        # convention of slowpath_addr{1,2} are tweaked a lot to allow
        # the code here to be just two CALLs: slowpath_addr1 gets the
        # size of the object to allocate from (EDX-EAX) and returns the
        # result in EAX; slowpath_addr2 additionally returns in EDX a
        # copy of heap(nursery_free_adr), so that the final MOV below is
        # a no-op.
        slowpath_addr1 = self.malloc_fixedsize_slowpath1
        # reserve room for the argument to the real malloc and the
        # 8 saved XMM regs
        self._regalloc.reserve_param(1+16)
        self.mc.CALL(imm(slowpath_addr1))
        self.mark_gc_roots()
        slowpath_addr2 = self.malloc_fixedsize_slowpath2
        self.mc.CALL(imm(slowpath_addr2))

        offset = self.mc.get_relative_pos() - jmp_adr
        assert 0 < offset <= 127
        self.mc.overwrite(jmp_adr-1, [chr(offset)])
        # on 64-bits, 'tid' is a value that fits in 31 bits
        self.mc.MOV_mi((eax.value, 0), tid)
        self.mc.MOV(heap(nursery_free_adr), edx)
        
genop_discard_list = [Assembler386.not_implemented_op_discard] * rop._LAST
genop_list = [Assembler386.not_implemented_op] * rop._LAST
genop_guard_list = [Assembler386.not_implemented_op_guard] * rop._LAST

for name, value in Assembler386.__dict__.iteritems():
    if name.startswith('genop_discard_'):
        opname = name[len('genop_discard_'):]
        num = getattr(rop, opname.upper())
        genop_discard_list[num] = value
    elif name.startswith('genop_guard_') and name != 'genop_guard_exception': 
        opname = name[len('genop_guard_'):]
        num = getattr(rop, opname.upper())
        genop_guard_list[num] = value
    elif name.startswith('genop_'):
        opname = name[len('genop_'):]
        num = getattr(rop, opname.upper())
        genop_list[num] = value

def round_up_to_4(size):
    if size < 4:
        return 4
    return size

# XXX: ri386 migration shims:
def addr_add(reg_or_imm1, reg_or_imm2, offset=0, scale=0):
    return AddressLoc(reg_or_imm1, reg_or_imm2, scale, offset)

def addr_add_const(reg_or_imm1, offset):
    return AddressLoc(reg_or_imm1, ImmedLoc(0), 0, offset)

def mem(loc, offset):
    return AddressLoc(loc, ImmedLoc(0), 0, offset)

def heap(addr):
    return AddressLoc(ImmedLoc(addr), ImmedLoc(0), 0, 0)

def not_implemented(msg):
    os.write(2, '[x86/asm] %s\n' % msg)
    raise NotImplementedError(msg)
