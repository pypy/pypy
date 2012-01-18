from __future__ import with_statement
import os
from pypy.jit.backend.arm.helper.assembler import saved_registers
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, DOUBLE_WORD, FUNC_ALIGN, \
                                    N_REGISTERS_SAVED_BY_MALLOC
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, OverwritingBuilder
from pypy.jit.backend.arm.regalloc import (Regalloc, ARMFrameManager,
                    ARMv7RegisterManager, check_imm_arg,
                    operations as regalloc_operations,
                    get_fp_offset,
                    operations_with_guard as regalloc_operations_with_guard)
from pypy.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from pypy.jit.backend.model import CompiledLoopToken
from pypy.jit.codewriter import longlong
from pypy.jit.metainterp.history import (AbstractFailDescr, INT, REF, FLOAT)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.jit.backend.arm.opassembler import ResOpAssembler
from pypy.rlib.debug import debug_print, debug_start, debug_stop

# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array, memcpy_fn


class AssemblerARM(ResOpAssembler):

    STACK_FIXED_AREA = -1

    debug = True

    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_float = values_array(longlong.FLOATSTORAGE,
                                                            failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.fail_boxes_count = 0
        self.fail_force_index = 0
        self.setup_failure_recovery()
        self.mc = None
        self.memcpy_addr = 0
        self.pending_guards = None
        self._exit_code_addr = 0
        self.current_clt = None
        self.malloc_slowpath = 0
        self._regalloc = None
        self.datablockwrapper = None
        self.propagate_exception_path = 0
        self._compute_stack_size()

    def _compute_stack_size(self):
        self.STACK_FIXED_AREA = len(r.callee_saved_registers) * WORD
        self.STACK_FIXED_AREA += WORD  # FORCE_TOKEN
        self.STACK_FIXED_AREA += N_REGISTERS_SAVED_BY_MALLOC * WORD
        if self.cpu.supports_floats:
            self.STACK_FIXED_AREA += (len(r.callee_saved_vfp_registers)
                                        * DOUBLE_WORD)
        if self.STACK_FIXED_AREA % 8 != 0:
            self.STACK_FIXED_AREA += WORD  # Stack alignment
        assert self.STACK_FIXED_AREA % 8 == 0

    def setup(self, looptoken, operations):
        self.current_clt = looptoken.compiled_loop_token
        operations = self.cpu.gc_ll_descr.rewrite_assembler(self.cpu,
                        operations, self.current_clt.allgcrefs)
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        self.mc = ARMv7Builder()
        self.pending_guards = []
        assert self.datablockwrapper is None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        self.datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                        allblocks)
        self.target_tokens_currently_compiling = {}
        return operations

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None
        assert self.datablockwrapper is None

    def setup_once(self):
        # Addresses of functions called by new_xxx operations
        gc_ll_descr = self.cpu.gc_ll_descr
        gc_ll_descr.initialize()
        self._build_propagate_exception_path()
        if gc_ll_descr.get_malloc_slowpath_addr is not None:
            self._build_malloc_slowpath()
        if gc_ll_descr.gcrootmap and gc_ll_descr.gcrootmap.is_shadow_stack:
            self._build_release_gil(gc_ll_descr.gcrootmap)
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self._exit_code_addr = self._gen_exit_path()
        self._leave_jitted_hook_save_exc = \
                                    self._gen_leave_jitted_hook_code(True)
        self._leave_jitted_hook = self._gen_leave_jitted_hook_code(False)

    @staticmethod
    def _release_gil_shadowstack():
        before = rffi.aroundstate.before
        if before:
            before()

    @staticmethod
    def _reacquire_gil_shadowstack():
        after = rffi.aroundstate.after
        if after:
            after()

    _NOARG_FUNC = lltype.Ptr(lltype.FuncType([], lltype.Void))

    def _build_release_gil(self, gcrootmap):
        assert gcrootmap.is_shadow_stack
        releasegil_func = llhelper(self._NOARG_FUNC,
                                   self._release_gil_shadowstack)
        reacqgil_func = llhelper(self._NOARG_FUNC,
                                 self._reacquire_gil_shadowstack)
        self.releasegil_addr = rffi.cast(lltype.Signed, releasegil_func)
        self.reacqgil_addr = rffi.cast(lltype.Signed, reacqgil_func)

    def _gen_leave_jitted_hook_code(self, save_exc):
        mc = ARMv7Builder()
        # XXX add a check if cpu supports floats
        with saved_registers(mc, r.caller_resp + [r.lr], r.caller_vfp_resp):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
            mc.BL(addr)
        assert self._exit_code_addr != 0
        mc.B(self._exit_code_addr)
        return mc.materialize(self.cpu.asmmemmgr, [],
                               self.cpu.gc_ll_descr.gcrootmap)

    def _build_propagate_exception_path(self):
        if self.cpu.propagate_exception_v < 0:
            return      # not supported (for tests, or non-translated)
        #
        mc = ARMv7Builder()
        # call on_leave_jitted_save_exc()
        # XXX add a check if cpu supports floats
        with saved_registers(mc, r.caller_resp + [r.ip], r.caller_vfp_resp):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=True,
                                                default_to_memoryerror=True)
            mc.BL(addr)
        mc.gen_load_int(r.ip.value, self.cpu.propagate_exception_v)
        mc.MOV_rr(r.r0.value, r.ip.value)
        self.gen_func_epilog(mc=mc)
        self.propagate_exception_path = mc.materialize(self.cpu.asmmemmgr, [])

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, frame_pointer, stack_pointer):
            """mem_loc is a structure in memory describing where the values for
            the failargs are stored.  frame loc is the address of the frame
            pointer for the frame to be decoded frame """
            vfp_registers = rffi.cast(rffi.LONGLONGP, stack_pointer)
            registers = rffi.ptradd(vfp_registers, len(r.all_vfp_regs))
            registers = rffi.cast(rffi.LONGP, registers)
            return self.decode_registers_and_descr(mem_loc, frame_pointer,
                                                    registers, vfp_registers)

        self.failure_recovery_func = failure_recovery_func

    recovery_func_sign = lltype.Ptr(lltype.FuncType([lltype.Signed] * 3,
                                                        lltype.Signed))

    @rgc.no_collect
    def decode_registers_and_descr(self, mem_loc, frame_pointer,
                                                registers, vfp_registers):
        """Decode locations encoded in memory at mem_loc and write the values
        to the failboxes.  Values for spilled vars and registers are stored on
        stack at frame_loc """
        assert frame_pointer & 1 == 0
        bytecode = rffi.cast(rffi.UCHARP, mem_loc)
        num = 0
        value = 0
        fvalue = 0
        code_inputarg = False
        while True:
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
                code = int((code - self.CODE_FROMSTACK) >> 2)
                if code_inputarg:
                    code = ~code
                    code_inputarg = False
                if kind == self.DESCR_FLOAT:
                    # we use code + 1 to get the hi word of the double worded float
                    stackloc = frame_pointer - get_fp_offset(int(code) + 1)
                    assert stackloc & 3 == 0
                    fvalue = rffi.cast(rffi.LONGLONGP, stackloc)[0]
                else:
                    stackloc = frame_pointer - get_fp_offset(int(code))
                    assert stackloc & 1 == 0
                    value = rffi.cast(rffi.LONGP, stackloc)[0]
            else:
                # 'code' identifies a register: load its value
                kind = code & 3
                if kind == self.DESCR_SPECIAL:
                    if code == self.CODE_HOLE:
                        num += 1
                        continue
                    if code == self.CODE_INPUTARG:
                        code_inputarg = True
                        continue
                    assert code == self.CODE_STOP
                    break
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    fvalue = vfp_registers[code]
                else:
                    value = registers[code]
            # store the loaded value into fail_boxes_<type>
            if kind == self.DESCR_FLOAT:
                tgt = self.fail_boxes_float.get_addr_for_num(num)
                rffi.cast(rffi.LONGLONGP, tgt)[0] = fvalue
            else:
                if kind == self.DESCR_INT:
                    tgt = self.fail_boxes_int.get_addr_for_num(num)
                elif kind == self.DESCR_REF:
                    assert (value & 3) == 0, "misaligned pointer"
                    tgt = self.fail_boxes_ptr.get_addr_for_num(num)
                else:
                    assert 0, "bogus kind"
                rffi.cast(rffi.LONGP, tgt)[0] = value
            num += 1
        self.fail_boxes_count = num
        fail_index = rffi.cast(rffi.INTP, bytecode)[0]
        fail_index = rffi.cast(lltype.Signed, fail_index)
        return fail_index

    def decode_inputargs(self, code):
        descr_to_box_type = [REF, INT, FLOAT]
        bytecode = rffi.cast(rffi.UCHARP, code)
        arglocs = []
        code_inputarg = False
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
                if code_inputarg:
                    code = ~code
                    code_inputarg = False
                loc = ARMFrameManager.frame_pos(code, descr_to_box_type[kind])
            elif code == self.CODE_STOP:
                break
            elif code == self.CODE_HOLE:
                continue
            elif code == self.CODE_INPUTARG:
                code_inputarg = True
                continue
            else:
                # 'code' identifies a register
                kind = code & 3
                code >>= 2
                if kind == self.DESCR_FLOAT:
                    loc = r.all_vfp_regs[code]
                else:
                    loc = r.all_regs[code]
            arglocs.append(loc)
        return arglocs[:]

    def _build_malloc_slowpath(self):
        mc = ARMv7Builder()
        assert self.cpu.supports_floats
        # We need to push two registers here because we are going to make a
        # call an therefore the stack needs to be 8-byte aligned
        mc.PUSH([r.ip.value, r.lr.value])
        with saved_registers(mc, [], r.all_vfp_regs):
            # At this point we know that the values we need to compute the size
            # are stored in r0 and r1.
            mc.SUB_rr(r.r0.value, r.r1.value, r.r0.value)
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
            # XXX replace with an STMxx operation
            for reg, ofs in ARMv7RegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
                mc.STR_ri(reg.value, r.fp.value, imm=ofs)
            mc.BL(addr)
            for reg, ofs in ARMv7RegisterManager.REGLOC_TO_COPY_AREA_OFS.items():
                mc.LDR_ri(reg.value, r.fp.value, imm=ofs)

        mc.CMP_ri(r.r0.value, 0)
        mc.B(self.propagate_exception_path, c=c.EQ)
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.gen_load_int(r.r1.value, nursery_free_adr)
        mc.LDR_ri(r.r1.value, r.r1.value)
        # see above
        mc.POP([r.ip.value, r.pc.value])

        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.malloc_slowpath = rawstart

    def propagate_memoryerror_if_r0_is_null(self):
        # see ../x86/assembler.py:propagate_memoryerror_if_eax_is_null
        self.mc.CMP_ri(r.r0.value, 0)
        self.mc.B(self.propagate_exception_path, c=c.EQ)

    def _gen_exit_path(self):
        mc = ARMv7Builder()
        decode_registers_addr = llhelper(self.recovery_func_sign,
                                            self.failure_recovery_func)
        self._insert_checks(mc)
        with saved_registers(mc, r.all_regs, r.all_vfp_regs):
            # move mem block address, to r0 to pass as
            mc.MOV_rr(r.r0.value, r.lr.value)
            # pass the current frame pointer as second param
            mc.MOV_rr(r.r1.value, r.fp.value)
            # pass the current stack pointer as third param
            mc.MOV_rr(r.r2.value, r.sp.value)
            self._insert_checks(mc)
            mc.BL(rffi.cast(lltype.Signed, decode_registers_addr))
            mc.MOV_rr(r.ip.value, r.r0.value)
        mc.MOV_rr(r.r0.value, r.ip.value)
        self.gen_func_epilog(mc=mc)
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    DESCR_REF       = 0x00
    DESCR_INT       = 0x01
    DESCR_FLOAT     = 0x02
    DESCR_SPECIAL   = 0x03
    CODE_FROMSTACK  = 64
    CODE_STOP       = 0 | DESCR_SPECIAL
    CODE_HOLE       = 4 | DESCR_SPECIAL
    CODE_INPUTARG   = 8 | DESCR_SPECIAL

    def gen_descr_encoding(self, descr, failargs, locs):
        assert self.mc is not None
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
                if loc.is_stack():
                    pos = loc.position
                    if pos < 0:
                        self.mc.writechar(chr(self.CODE_INPUTARG))
                        pos = ~pos
                    n = self.CODE_FROMSTACK // 4 + pos
                else:
                    assert loc.is_reg() or loc.is_vfp_reg()
                    n = loc.value
                n = kind + 4 * n
                while n > 0x7F:
                    self.mc.writechar(chr((n & 0x7F) | 0x80))
                    n >>= 7
            else:
                n = self.CODE_HOLE
            self.mc.writechar(chr(n))
        self.mc.writechar(chr(self.CODE_STOP))

        fdescr = self.cpu.get_fail_descr_number(descr)
        self.mc.write32(fdescr)
        self.align()

        # assert that the fail_boxes lists are big enough
        assert len(failargs) <= self.fail_boxes_int.SIZE

    def _gen_path_to_exit_path(self, descr, args, arglocs,
                                            save_exc, fcond=c.AL):
        assert isinstance(save_exc, bool)
        self.gen_exit_code(self.mc, save_exc, fcond)
        self.gen_descr_encoding(descr, args, arglocs[1:])

    def gen_exit_code(self, mc, save_exc, fcond=c.AL):
        assert isinstance(save_exc, bool)
        if save_exc:
            path = self._leave_jitted_hook_save_exc
        else:
            path = self._leave_jitted_hook
        mc.BL(path)

    def align(self):
        while(self.mc.currpos() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    def gen_func_epilog(self, mc=None, cond=c.AL):
        stack_size = self.STACK_FIXED_AREA
        stack_size -= len(r.callee_saved_registers) * WORD
        if self.cpu.supports_floats:
            stack_size -= len(r.callee_saved_vfp_registers) * 2 * WORD

        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if mc is None:
            mc = self.mc
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_footer_shadowstack(gcrootmap, mc)
        mc.MOV_rr(r.sp.value, r.fp.value, cond=cond)
        mc.ADD_ri(r.sp.value, r.sp.value, stack_size, cond=cond)
        if self.cpu.supports_floats:
            mc.VPOP([reg.value for reg in r.callee_saved_vfp_registers],
                                                                    cond=cond)
        mc.POP([reg.value for reg in r.callee_restored_registers], cond=cond)

    def gen_func_prolog(self):
        stack_size = self.STACK_FIXED_AREA
        stack_size -= len(r.callee_saved_registers) * WORD
        if self.cpu.supports_floats:
            stack_size -= len(r.callee_saved_vfp_registers) * 2 * WORD

        self.mc.PUSH([reg.value for reg in r.callee_saved_registers])
        if self.cpu.supports_floats:
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
        # here we modify the stack pointer to leave room for the 9 registers
        # that are going to be saved here around malloc calls and one word to
        # store the force index
        self.mc.SUB_ri(r.sp.value, r.sp.value, stack_size)
        self.mc.MOV_rr(r.fp.value, r.sp.value)
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_shadowstack_header(gcrootmap)

    def gen_shadowstack_header(self, gcrootmap):
        # we need to put two words into the shadowstack: the MARKER
        # and the address of the frame (ebp, actually)
        # XXX add some comments
        rst = gcrootmap.get_root_stack_top_addr()
        self.mc.gen_load_int(r.ip.value, rst)
        self.mc.LDR_ri(r.r4.value, r.ip.value)  # LDR r4, [rootstacktop]
        self.mc.ADD_ri(r.r5.value, r.r4.value,
                                    imm=2 * WORD)  # ADD r5, r4 [2*WORD]
        self.mc.gen_load_int(r.r6.value, gcrootmap.MARKER)
        self.mc.STR_ri(r.r6.value, r.r4.value)
        self.mc.STR_ri(r.fp.value, r.r4.value, WORD)
        self.mc.STR_ri(r.r5.value, r.ip.value)

    def gen_footer_shadowstack(self, gcrootmap, mc):
        rst = gcrootmap.get_root_stack_top_addr()
        mc.gen_load_int(r.ip.value, rst)
        mc.LDR_ri(r.r4.value, r.ip.value)  # LDR r4, [rootstacktop]
        mc.SUB_ri(r.r5.value, r.r4.value, imm=2 * WORD)  # ADD r5, r4 [2*WORD]
        mc.STR_ri(r.r5.value, r.ip.value)

    def _dump(self, ops, type='loop'):
        debug_start('jit-backend-ops')
        debug_print(type)
        for op in ops:
            debug_print(op.repr())
        debug_stop('jit-backend-ops')

    def _call_header(self):
        self.align()
        self.gen_func_prolog()

    # cpu interface
    def assemble_loop(self, inputargs, operations, looptoken, log):
        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt.allgcrefs = []
        looptoken.compiled_loop_token = clt
        clt._debug_nbargs = len(inputargs)

        if not we_are_translated():
            # Arguments should be unique
            assert len(set(inputargs)) == len(inputargs)

        operations = self.setup(looptoken, operations)
        self._dump(operations)

        self._call_header()
        sp_patch_location = self._prepare_sp_patch_position()

        regalloc = Regalloc(assembler=self, frame_manager=ARMFrameManager())
        regalloc.prepare_loop(inputargs, operations)

        loop_head = self.mc.currpos()
        looptoken._arm_loop_code = loop_head

        clt.frame_depth = -1
        frame_depth = self._assemble(operations, regalloc)
        clt.frame_depth = frame_depth
        self._patch_sp_offset(sp_patch_location, frame_depth)

        self.write_pending_failure_recoveries()

        rawstart = self.materialize_loop(looptoken)
        looptoken._arm_func_addr = rawstart

        self.process_pending_guards(rawstart)
        self.fixup_target_tokens(rawstart)

        if log and not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(rawstart,
                    'loop_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling loop with token %r' % looptoken
        self.teardown()

    def _assemble(self, operations, regalloc):
        regalloc.compute_hint_frame_locations(operations)
        #self.mc.BKPT()
        self._walk_operations(operations, regalloc)
        frame_depth = regalloc.frame_manager.get_frame_depth()
        jump_target_descr = regalloc.jump_target_descr
        if jump_target_descr is not None:
            frame_depth = max(frame_depth,
                                jump_target_descr._arm_clt.frame_depth)
        return frame_depth

    def assemble_bridge(self, faildescr, inputargs, operations,
                                                    original_loop_token, log):
        operations = self.setup(original_loop_token, operations)
        self._dump(operations, 'bridge')
        assert isinstance(faildescr, AbstractFailDescr)
        code = self._find_failure_recovery_bytecode(faildescr)
        frame_depth = faildescr._arm_current_frame_depth
        arglocs = self.decode_inputargs(code)
        if not we_are_translated():
            assert len(inputargs) == len(arglocs)

        regalloc = Regalloc(assembler=self, frame_manager=ARMFrameManager())
        regalloc.prepare_bridge(inputargs, arglocs, operations)

        sp_patch_location = self._prepare_sp_patch_position()

        frame_depth = self._assemble(operations, regalloc)

        self._patch_sp_offset(sp_patch_location, frame_depth)

        self.write_pending_failure_recoveries()
        rawstart = self.materialize_loop(original_loop_token)
        self.process_pending_guards(rawstart)

        self.patch_trace(faildescr, original_loop_token,
                                    rawstart, regalloc)
        self.fixup_target_tokens(rawstart)

        if not we_are_translated():
            # for the benefit of tests
            faildescr._arm_bridge_frame_depth = frame_depth
            if log:
                print 'Bridge', inputargs, operations
                self.mc._dump_trace(rawstart, 'bridge_%d.asm' %
                self.cpu.total_compiled_bridges)
        self.current_clt.frame_depth = max(self.current_clt.frame_depth,
                                                                frame_depth)
        self.teardown()

    def _find_failure_recovery_bytecode(self, faildescr):
        guard_addr = faildescr._arm_block_start + faildescr._arm_guard_pos
        # a guard requires 3 words to encode the jump to the exit code.
        return guard_addr + 3 * WORD

    def fixup_target_tokens(self, rawstart):
        for targettoken in self.target_tokens_currently_compiling:
            targettoken._arm_loop_code += rawstart
        self.target_tokens_currently_compiling = None

    def target_arglocs(self, loop_token):
        return loop_token._arm_arglocs

    def materialize_loop(self, looptoken):
        self.datablockwrapper.done()      # finish using cpu.asmmemmgr
        self.datablockwrapper = None
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        return self.mc.materialize(self.cpu.asmmemmgr, allblocks,
                                   self.cpu.gc_ll_descr.gcrootmap)

    def write_pending_failure_recoveries(self):
        for tok in self.pending_guards:
            descr = tok.descr
            #generate the exit stub and the encoded representation
            pos = self.mc.currpos()
            tok.pos_recovery_stub = pos

            self._gen_path_to_exit_path(descr, tok.failargs,
                                        tok.faillocs, save_exc=tok.save_exc)
            # store info on the descr
            descr._arm_current_frame_depth = tok.faillocs[0].getint()
            descr._arm_guard_pos = pos

    def process_pending_guards(self, block_start):
        clt = self.current_clt
        for tok in self.pending_guards:
            descr = tok.descr
            assert isinstance(descr, AbstractFailDescr)

            #XXX _arm_block_start should go in the looptoken
            descr._arm_block_start = block_start

            if not tok.is_invalidate:
                #patch the guard jumpt to the stub
                # overwrite the generate NOP with a B_offs to the pos of the
                # stub
                mc = ARMv7Builder()
                mc.B_offs(descr._arm_guard_pos - tok.offset,
                                    c.get_opposite_of(tok.fcond))
                mc.copy_to_raw_memory(block_start + tok.offset)
            else:
                clt.invalidate_positions.append(
                (block_start + tok.offset, descr._arm_guard_pos - tok.offset))

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def _prepare_sp_patch_position(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update
        the sp according to the number of spilled variables"""
        size = (self.mc.size_of_gen_load_int + WORD)
        l = self.mc.currpos()
        for _ in range(size // WORD):
            self.mc.NOP()
        return l

    def _patch_sp_offset(self, pos, frame_depth):
        cb = OverwritingBuilder(self.mc, pos,
                                OverwritingBuilder.size_of_gen_load_int + WORD)
        # Note: the frame_depth is one less than the value stored in the frame
        # manager
        n = frame_depth * WORD

        # ensure the sp is 8 byte aligned when patching it
        if n % 8 != 0:
            n += WORD
        assert n % 8 == 0

        self._adjust_sp(n, cb, base_reg=r.fp)

    def _adjust_sp(self, n, cb=None, fcond=c.AL, base_reg=r.sp):
        if cb is None:
            cb = self.mc
        if n < 0:
            n = -n
            rev = True
        else:
            rev = False
        if n <= 0xFF and fcond == c.AL:
            if rev:
                cb.ADD_ri(r.sp.value, base_reg.value, n)
            else:
                cb.SUB_ri(r.sp.value, base_reg.value, n)
        else:
            cb.gen_load_int(r.ip.value, n, cond=fcond)
            if rev:
                cb.ADD_rr(r.sp.value, base_reg.value, r.ip.value, cond=fcond)
            else:
                cb.SUB_rr(r.sp.value, base_reg.value, r.ip.value, cond=fcond)

    def _walk_operations(self, operations, regalloc):
        fcond = c.AL
        self._regalloc = regalloc
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            i = regalloc.position()
            op = operations[i]
            opnum = op.getopnum()
            if op.has_no_side_effect() and op.result not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            elif self.can_merge_with_next_guard(op, i, operations):
                guard = operations[i + 1]
                assert guard.is_guard()
                arglocs = regalloc_operations_with_guard[opnum](regalloc, op,
                                        guard, fcond)
                fcond = asm_operations_with_guard[opnum](self, op,
                                        guard, arglocs, regalloc, fcond)
                regalloc.next_instruction()
                regalloc.possibly_free_vars_for_op(guard)
                regalloc.possibly_free_vars(guard.getfailargs())
            elif not we_are_translated() and op.getopnum() == -124:
                regalloc.prepare_force_spill(op, fcond)
            else:
                arglocs = regalloc_operations[opnum](regalloc, op, fcond)
                if arglocs is not None:
                    fcond = asm_operations[opnum](self, op, arglocs,
                                                        regalloc, fcond)
            if op.is_guard():
                regalloc.possibly_free_vars(op.getfailargs())
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc.free_temp_vars()
            regalloc._check_invariants()

    # from ../x86/regalloc.py
    def can_merge_with_next_guard(self, op, i, operations):
        if (op.getopnum() == rop.CALL_MAY_FORCE or
            op.getopnum() == rop.CALL_ASSEMBLER or
            op.getopnum() == rop.CALL_RELEASE_GIL):
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if not op.is_comparison():
            if op.is_ovf():
                if (operations[i + 1].getopnum() != rop.GUARD_NO_OVERFLOW and
                    operations[i + 1].getopnum() != rop.GUARD_OVERFLOW):
                    not_implemented("int_xxx_ovf not followed by "
                                    "guard_(no)_overflow")
                return True
            return False
        if (operations[i + 1].getopnum() != rop.GUARD_TRUE and
            operations[i + 1].getopnum() != rop.GUARD_FALSE):
            return False
        if operations[i + 1].getarg(0) is not op.result:
            return False
        if (self._regalloc.longevity[op.result][1] > i + 1 or
            op.result in operations[i + 1].getfailargs()):
            return False
        return True

    def _insert_checks(self, mc=None):
        if not we_are_translated():
            if mc is None:
                mc = self.mc
            mc.CMP_rr(r.fp.value, r.sp.value)
            mc.MOV_rr(r.pc.value, r.pc.value, cond=c.GE)
            mc.BKPT()

    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == 4:
            return
        if size == 1:
            if not signed:  # unsigned char
                self.mc.AND_ri(resloc.value, resloc.value, 0xFF)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 24)
                self.mc.ASR_ri(resloc.value, resloc.value, 24)
        elif size == 2:
            if not signed:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.LSR_ri(resloc.value, resloc.value, 16)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.ASR_ri(resloc.value, resloc.value, 16)

    def patch_trace(self, faildescr, looptoken, bridge_addr, regalloc):
        # The first instruction (word) is not overwritten, because it is the
        # one that actually checks the condition
        b = ARMv7Builder()
        patch_addr = faildescr._arm_block_start + faildescr._arm_guard_pos
        b.B(bridge_addr)
        b.copy_to_raw_memory(patch_addr)

    # regalloc support
    def load(self, loc, value):
        assert (loc.is_reg() and value.is_imm()
                    or loc.is_vfp_reg() and value.is_imm_float())
        if value.is_imm():
            self.mc.gen_load_int(loc.value, value.getint())
        elif value.is_imm_float():
            self.mc.gen_load_int(r.ip.value, value.getint())
            self.mc.VLDR(loc.value, r.ip.value)

    def _mov_imm_to_loc(self, prev_loc, loc, cond=c.AL):
        if not loc.is_reg() and not (loc.is_stack() and loc.type != FLOAT):
            raise AssertionError("invalid target for move from imm value")
        if loc.is_reg():
            new_loc = loc
        elif loc.is_stack():
            self.mc.PUSH([r.lr.value], cond=cond)
            new_loc = r.lr
        else:
            raise AssertionError("invalid target for move from imm value")
        self.mc.gen_load_int(new_loc.value, prev_loc.value, cond=cond)
        if loc.is_stack():
            self.regalloc_mov(new_loc, loc)
            self.mc.POP([r.lr.value], cond=cond)

    def _mov_reg_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_imm():
            raise AssertionError("mov reg to imm doesn't make sense")
        if loc.is_reg():
            self.mc.MOV_rr(loc.value, prev_loc.value, cond=cond)
        elif loc.is_stack() and loc.type != FLOAT:
            # spill a core register
            if prev_loc is r.ip:
                temp = r.lr
            else:
                temp = r.ip
            offset = loc.value
            if not check_imm_arg(offset, size=0xFFF):
                self.mc.PUSH([temp.value], cond=cond)
                self.mc.gen_load_int(temp.value, -offset, cond=cond)
                self.mc.STR_rr(prev_loc.value, r.fp.value,
                                            temp.value, cond=cond)
                self.mc.POP([temp.value], cond=cond)
            else:
                self.mc.STR_ri(prev_loc.value, r.fp.value,
                                            imm=-offset, cond=cond)
        else:
            assert 0, 'unsupported case'

    def _mov_stack_to_loc(self, prev_loc, loc, cond=c.AL):
        pushed = False
        if loc.is_reg():
            assert prev_loc.type != FLOAT, 'trying to load from an \
                incompatible location into a core register'
            assert loc is not r.lr, 'lr is not supported as a target \
                when moving from the stack'
            # unspill a core register
            offset = prev_loc.value
            if not check_imm_arg(offset, size=0xFFF):
                self.mc.PUSH([r.lr.value], cond=cond)
                pushed = True
                self.mc.gen_load_int(r.lr.value, -offset, cond=cond)
                self.mc.LDR_rr(loc.value, r.fp.value, r.lr.value, cond=cond)
            else:
                self.mc.LDR_ri(loc.value, r.fp.value, imm=-offset, cond=cond)
            if pushed:
                self.mc.POP([r.lr.value], cond=cond)
        elif loc.is_vfp_reg():
            assert prev_loc.type == FLOAT, 'trying to load from an \
                incompatible location into a float register'
            # load spilled value into vfp reg
            offset = prev_loc.value
            self.mc.PUSH([r.ip.value], cond=cond)
            pushed = True
            if not check_imm_arg(offset):
                self.mc.gen_load_int(r.ip.value, offset, cond=cond)
                self.mc.SUB_rr(r.ip.value, r.fp.value, r.ip.value, cond=cond)
            else:
                self.mc.SUB_ri(r.ip.value, r.fp.value, offset, cond=cond)
            self.mc.VLDR(loc.value, r.ip.value, cond=cond)
            if pushed:
                self.mc.POP([r.ip.value], cond=cond)
        else:
            assert 0, 'unsupported case'

    def _mov_imm_float_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_vfp_reg():
            self.mc.PUSH([r.ip.value], cond=cond)
            self.mc.gen_load_int(r.ip.value, prev_loc.getint(), cond=cond)
            self.mc.VLDR(loc.value, r.ip.value, cond=cond)
            self.mc.POP([r.ip.value], cond=cond)
        elif loc.is_stack():
            self.regalloc_push(r.vfp_ip)
            self.regalloc_mov(prev_loc, r.vfp_ip, cond)
            self.regalloc_mov(r.vfp_ip, loc, cond)
            self.regalloc_pop(r.vfp_ip)
        else:
            assert 0, 'unsupported case'

    def _mov_vfp_reg_to_loc(self, prev_loc, loc, cond=c.AL):
        if loc.is_vfp_reg():
            self.mc.VMOV_cc(loc.value, prev_loc.value, cond=cond)
        elif loc.is_stack():
            assert loc.type == FLOAT, 'trying to store to an \
                incompatible location from a float register'
            # spill vfp register
            self.mc.PUSH([r.ip.value], cond=cond)
            offset = loc.value
            if not check_imm_arg(offset):
                self.mc.gen_load_int(r.ip.value, offset, cond=cond)
                self.mc.SUB_rr(r.ip.value, r.fp.value, r.ip.value, cond=cond)
            else:
                self.mc.SUB_ri(r.ip.value, r.fp.value, offset, cond=cond)
            self.mc.VSTR(prev_loc.value, r.ip.value, cond=cond)
            self.mc.POP([r.ip.value], cond=cond)
        else:
            assert 0, 'unsupported case'

    def regalloc_mov(self, prev_loc, loc, cond=c.AL):
        """Moves a value from a previous location to some other location"""
        if prev_loc.is_imm():
            return self._mov_imm_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_reg():
            self._mov_reg_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_stack():
            self._mov_stack_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_imm_float():
            self._mov_imm_float_to_loc(prev_loc, loc, cond)
        elif prev_loc.is_vfp_reg():
            self._mov_vfp_reg_to_loc(prev_loc, loc, cond)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def mov_from_vfp_loc(self, vfp_loc, reg1, reg2, cond=c.AL):
        """Moves floating point values either as an immediate, in a vfp
        register or at a stack location to a pair of core registers"""
        assert reg1.value + 1 == reg2.value
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_rc(reg1.value, reg2.value, vfp_loc.value, cond=cond)
        elif vfp_loc.is_imm_float():
            self.mc.PUSH([r.ip.value], cond=cond)
            self.mc.gen_load_int(r.ip.value, vfp_loc.getint(), cond=cond)
            # we need to load one word to loc and one to loc+1 which are
            # two 32-bit core registers
            self.mc.LDR_ri(reg1.value, r.ip.value, cond=cond)
            self.mc.LDR_ri(reg2.value, r.ip.value, imm=WORD, cond=cond)
            self.mc.POP([r.ip.value], cond=cond)
        elif vfp_loc.is_stack() and vfp_loc.type == FLOAT:
            # load spilled vfp value into two core registers
            offset = vfp_loc.value
            if not check_imm_arg(offset, size=0xFFF):
                self.mc.PUSH([r.ip.value], cond=cond)
                self.mc.gen_load_int(r.ip.value, -offset, cond=cond)
                self.mc.LDR_rr(reg1.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.ADD_ri(r.ip.value, r.ip.value, imm=WORD, cond=cond)
                self.mc.LDR_rr(reg2.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.POP([r.ip.value], cond=cond)
            else:
                self.mc.LDR_ri(reg1.value, r.fp.value, imm=-offset, cond=cond)
                self.mc.LDR_ri(reg2.value, r.fp.value,
                                                imm=-offset + WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def mov_to_vfp_loc(self, reg1, reg2, vfp_loc, cond=c.AL):
        """Moves a floating point value from to consecutive core registers to a
        vfp location, either a vfp regsiter or a stacklocation"""
        assert reg1.value + 1 == reg2.value
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_cr(vfp_loc.value, reg1.value, reg2.value, cond=cond)
        elif vfp_loc.is_stack():
            # move from two core registers to a float stack location
            offset = vfp_loc.value
            if not check_imm_arg(offset, size=0xFFF):
                self.mc.PUSH([r.ip.value], cond=cond)
                self.mc.gen_load_int(r.ip.value, -offset, cond=cond)
                self.mc.STR_rr(reg1.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.ADD_ri(r.ip.value, r.ip.value, imm=WORD, cond=cond)
                self.mc.STR_rr(reg2.value, r.fp.value, r.ip.value, cond=cond)
                self.mc.POP([r.ip.value], cond=cond)
            else:
                self.mc.STR_ri(reg1.value, r.fp.value, imm=-offset, cond=cond)
                self.mc.STR_ri(reg2.value, r.fp.value,
                                                imm=-offset + WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def regalloc_push(self, loc, cond=c.AL):
        """Pushes the value stored in loc to the stack
        Can trash the current value of the IP register when pushing a stack
        loc"""

        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_mov(loc, scratch_reg, cond)
            self.regalloc_push(scratch_reg, cond)
        elif loc.is_reg():
            self.mc.PUSH([loc.value], cond=cond)
        elif loc.is_vfp_reg():
            self.mc.VPUSH([loc.value], cond=cond)
        elif loc.is_imm():
            self.regalloc_mov(loc, r.ip)
            self.mc.PUSH([r.ip.value], cond=cond)
        elif loc.is_imm_float():
            self.regalloc_mov(loc, r.vfp_ip)
            self.mc.VPUSH([r.vfp_ip.value], cond=cond)
        else:
            raise AssertionError('Trying to push an invalid location')

    def regalloc_pop(self, loc, cond=c.AL):
        """Pops the value on top of the stack to loc Can trash the current
        value of the IP register when popping to a stack loc"""
        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_pop(scratch_reg)
            self.regalloc_mov(scratch_reg, loc)
        elif loc.is_reg():
            self.mc.POP([loc.value], cond=cond)
        elif loc.is_vfp_reg():
            self.mc.VPOP([loc.value], cond=cond)
        else:
            raise AssertionError('Trying to pop to an invalid location')

    def leave_jitted_hook(self):
        ptrs = self.fail_boxes_ptr.ar
        llop.gc_assume_young_pointers(lltype.Void,
                                      llmemory.cast_ptr_to_adr(ptrs))

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size):
        assert size & (WORD-1) == 0     # must be correctly aligned

        self.mc.gen_load_int(r.r0.value, nursery_free_adr)
        self.mc.LDR_ri(r.r0.value, r.r0.value)

        if check_imm_arg(size):
            self.mc.ADD_ri(r.r1.value, r.r0.value, size)
        else:
            self.mc.gen_load_int(r.r1.value, size)
            self.mc.ADD_rr(r.r1.value, r.r0.value, r.r1.value)

        # XXX maybe use an offset from the value nursery_free_addr
        self.mc.gen_load_int(r.ip.value, nursery_top_adr)
        self.mc.LDR_ri(r.ip.value, r.ip.value)

        self.mc.CMP_rr(r.r1.value, r.ip.value)

        # XXX update
        # See comments in _build_malloc_slowpath for the
        # details of the two helper functions that we are calling below.
        # First, we need to call two of them and not just one because we
        # need to have a mark_gc_roots() in between.  Then the calling
        # convention of slowpath_addr{1,2} are tweaked a lot to allow
        # the code here to be just two CALLs: slowpath_addr1 gets the
        # size of the object to allocate from (EDX-EAX) and returns the
        # result in EAX; self.malloc_slowpath additionally returns in EDX a
        # copy of heap(nursery_free_adr), so that the final MOV below is
        # a no-op.
        self.mark_gc_roots(self.write_new_force_index(),
                           use_copy_area=True)
        self.mc.BL(self.malloc_slowpath, c=c.HI)

        self.mc.gen_load_int(r.ip.value, nursery_free_adr)
        self.mc.STR_ri(r.r1.value, r.ip.value)

    def mark_gc_roots(self, force_index, use_copy_area=False):
        if force_index < 0:
            return     # not needed
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap:
            mark = self._regalloc.get_mark_gc_roots(gcrootmap, use_copy_area)
            assert gcrootmap.is_shadow_stack
            gcrootmap.write_callshape(mark, force_index)

    def write_new_force_index(self):
        # for shadowstack only: get a new, unused force_index number and
        # write it to FORCE_INDEX_OFS.  Used to record the call shape
        # (i.e. where the GC pointers are in the stack) around a CALL
        # instruction that doesn't already have a force_index.
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            clt = self.current_clt
            force_index = clt.reserve_and_record_some_faildescr_index()
            self._write_fail_index(force_index)
            return force_index
        else:
            return 0


def not_implemented(msg):
    os.write(2, '[ARM/asm] %s\n' % msg)
    raise NotImplementedError(msg)


def notimplemented_op(self, op, arglocs, regalloc, fcond):
    print "[ARM/asm] %s not implemented" % op.getopname()
    raise NotImplementedError(op)


def notimplemented_op_with_guard(self, op, guard_op, arglocs, regalloc, fcond):
    print "[ARM/asm] %s with guard %s not implemented" % \
                        (op.getopname(), guard_op.getopname())
    raise NotImplementedError(op)

asm_operations = [notimplemented_op] * (rop._LAST + 1)
asm_operations_with_guard = [notimplemented_op_with_guard] * (rop._LAST + 1)

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_op_%s' % key
    if hasattr(AssemblerARM, methname):
        func = getattr(AssemblerARM, methname).im_func
        asm_operations[value] = func

for key, value in rop.__dict__.items():
    key = key.lower()
    if key.startswith('_'):
        continue
    methname = 'emit_guard_%s' % key
    if hasattr(AssemblerARM, methname):
        func = getattr(AssemblerARM, methname).im_func
        asm_operations_with_guard[value] = func
