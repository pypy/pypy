from pypy.jit.backend.arm.helper.assembler import saved_registers
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, FUNC_ALIGN, PC_OFFSET
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, OverwritingBuilder
from pypy.jit.backend.arm.regalloc import (Regalloc, ARMFrameManager,
                                                    _check_imm_arg, TempInt, TempPtr)
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity, TempBox
from pypy.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from pypy.jit.backend.model import CompiledLoopToken
from pypy.jit.codewriter import longlong
from pypy.jit.metainterp.history import (Const, ConstInt, ConstPtr,
                                        BoxInt, BoxPtr, AbstractFailDescr,
                                        INT, REF, FLOAT)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.longlong2float import float2longlong, longlong2float
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rarithmetic import r_uint, r_longlong
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.jit.backend.arm.opassembler import ResOpAssembler
from pypy.rlib.debug import (debug_print, debug_start, debug_stop,
                             have_debug_prints)

# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

class AssemblerARM(ResOpAssembler):
    """
    Encoding for locations in memory
    types:
    \xEE = REF
    \xEF = INT
    location:
    \xFC = stack location
    \xFD = imm location
    emtpy = reg location
    \xFE = Empty loc

    \xFF = END_OF_LOCS
    """
    FLOAT_TYPE = '\xED'
    REF_TYPE   = '\xEE'
    INT_TYPE   = '\xEF'

    STACK_LOC = '\xFC'
    IMM_LOC = '\xFD'
    # REG_LOC is empty
    EMPTY_LOC = '\xFE'

    END_OF_LOCS = '\xFF'


    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_float = values_array(longlong.FLOATSTORAGE, failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.fail_boxes_count = 0
        self.fail_force_index = 0
        self.setup_failure_recovery()
        self.mc = None
        self.malloc_func_addr = 0
        self.malloc_array_func_addr = 0
        self.malloc_str_func_addr = 0
        self.malloc_unicode_func_addr = 0
        self.memcpy_addr = 0
        self.teardown()
        self._exit_code_addr = 0

    def setup(self):
        assert self.memcpy_addr != 0, 'setup_once() not called?'
        self.mc = ARMv7Builder()
        self.guard_descrs = []
        self.blocks = []

    def setup_once(self):
        # Addresses of functions called by new_xxx operations
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
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self._exit_code_addr = self._gen_exit_path()
        self._leave_jitted_jook_save_exc = self._gen_leave_jitted_hook_code(True)
        self._leave_jitted_jook = self._gen_leave_jitted_hook_code(False)

    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, frame_pointer, stack_pointer):
            """mem_loc is a structure in memory describing where the values for
            the failargs are stored.
            frame loc is the address of the frame pointer for the frame to be
            decoded frame """
            return self.decode_registers_and_descr(mem_loc, frame_pointer, stack_pointer)

        self.failure_recovery_func = failure_recovery_func

    recovery_func_sign = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed, lltype.Signed], lltype.Signed))

    @rgc.no_collect
    def decode_registers_and_descr(self, mem_loc, frame_loc, regs_loc):
        """Decode locations encoded in memory at mem_loc and write the values to
        the failboxes.
        Values for spilled vars and registers are stored on stack at frame_loc
        """
        enc = rffi.cast(rffi.CCHARP, mem_loc)
        frame_depth = frame_loc - (regs_loc + len(r.all_regs)*WORD + len(r.all_vfp_regs)*2*WORD)
        stack = rffi.cast(rffi.CCHARP, frame_loc - frame_depth)
        vfp_regs = rffi.cast(rffi.CCHARP, regs_loc)
        regs = rffi.cast(rffi.CCHARP, regs_loc + len(r.all_vfp_regs)*2*WORD)
        i = -1
        fail_index = -1
        while(True):
            i += 1
            fail_index += 1
            res = enc[i]
            if res == self.END_OF_LOCS:
                break
            if res == self.EMPTY_LOC:
                continue

            group = res
            i += 1
            res = enc[i]
            if res == self.IMM_LOC:
                assert group == self.INT_TYPE or group == self.REF_TYPE
                # imm value
                value = self.decode32(enc, i+1)
                i += 4
            elif res == self.STACK_LOC:
                stack_loc = self.decode32(enc, i+1)
                if group == self.FLOAT_TYPE:
                    value = self.decode64(stack, frame_depth - stack_loc*WORD)
                else:
                    value = self.decode32(stack, frame_depth - stack_loc*WORD)
                i += 4
            else: # REG_LOC
                reg = ord(enc[i])
                if group == self.FLOAT_TYPE:
                    value = self.decode64(vfp_regs, reg*2*WORD)
                else:
                    value = self.decode32(regs, reg*WORD)

            if group == self.INT_TYPE:
                self.fail_boxes_int.setitem(fail_index, value)
            elif group == self.REF_TYPE:
                tgt = self.fail_boxes_ptr.get_addr_for_num(fail_index)
                rffi.cast(rffi.LONGP, tgt)[0] = value
                #self.fail_boxes_ptr.setitem(fail_index, value)# rffi.cast(llmemory.GCREF, value))
            elif group == self.FLOAT_TYPE:
                self.fail_boxes_float.setitem(fail_index, value)
            else:
                assert 0, 'unknown type'


        assert enc[i] == self.END_OF_LOCS
        descr = self.decode32(enc, i+1)
        self.fail_boxes_count = fail_index
        self.fail_force_index = frame_loc
        return descr

    def decode_inputargs(self, enc, inputargs, regalloc):
        locs = []
        j = 0
        for i in range(len(inputargs)):
            res = enc[j]
            if res == self.END_OF_LOCS:
                assert 0, 'reached end of encoded area'
            while res == self.EMPTY_LOC:
                j += 1
                res = enc[j]

            assert res in [self.FLOAT_TYPE, self.INT_TYPE, self.REF_TYPE], 'location type is not supported'
            res_type = res
            j += 1
            res = enc[j]
            if res == self.IMM_LOC:
                # XXX decode imm if necessary
                assert 0, 'Imm Locations are not supported'
            elif res == self.STACK_LOC:
                if res_type == FLOAT:
                    assert 0, 'float on stack'
                stack_loc = self.decode32(enc, j+1)
                loc = regalloc.frame_manager.frame_pos(stack_loc, INT)
                j += 4
            else: # REG_LOC
                if res_type == self.FLOAT_TYPE:
                    loc = r.all_vfp_regs[ord(res)]
                else:
                    loc = r.all_regs[ord(res)]
            j += 1
            locs.append(loc)
        return locs

    def decode32(self, mem, index):
        highval = ord(mem[index+3])
        if highval >= 128:
            highval -= 256
        return (ord(mem[index])
                | ord(mem[index+1]) << 8
                | ord(mem[index+2]) << 16
                | highval << 24)

    def decode64(self, mem, index):
        low = self.decode32(mem, index)
        index += 4
        high = self.decode32(mem, index)
        return r_longlong(high << 32) | r_longlong(r_uint(low))

    def encode32(self, mem, i, n):
        mem[i] = chr(n & 0xFF)
        mem[i+1] = chr((n >> 8) & 0xFF)
        mem[i+2] = chr((n >> 16) & 0xFF)
        mem[i+3] = chr((n >> 24) & 0xFF)

    def _gen_leave_jitted_hook_code(self, save_exc=False):
        mc = ARMv7Builder()
        # XXX add a check if cpu supports floats 
        with saved_registers(mc, r.caller_resp + [r.ip], r.caller_vfp_resp):
            addr = self.cpu.get_on_leave_jitted_int(save_exception=save_exc)
            mc.BL(addr)
        assert self._exit_code_addr != 0
        mc.B(self._exit_code_addr)
        return mc.materialize(self.cpu.asmmemmgr, [],
                               self.cpu.gc_ll_descr.gcrootmap)
    def _gen_exit_path(self):
        mc = ARMv7Builder()
        decode_registers_addr = llhelper(self.recovery_func_sign, self.failure_recovery_func)

        with saved_registers(mc, r.all_regs, r.all_vfp_regs):
            mc.MOV_rr(r.r0.value, r.ip.value) # move mem block address, to r0 to pass as
            mc.MOV_rr(r.r1.value, r.fp.value) # pass the current frame pointer as second param
            mc.MOV_rr(r.r2.value, r.sp.value) # pass the current stack pointer as third param

            mc.BL(rffi.cast(lltype.Signed, decode_registers_addr))
            mc.MOV_rr(r.ip.value, r.r0.value)
        mc.MOV_rr(r.r0.value, r.ip.value)
        self.gen_func_epilog(mc=mc)
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    def _gen_path_to_exit_path(self, op, args, arglocs, fcond=c.AL, save_exc=False):
        descr = op.getdescr()
        if op.getopnum() != rop.FINISH:
            assert isinstance(descr, AbstractFailDescr)
            descr._arm_frame_depth = arglocs[0].getint()
        # The size of the allocated memory is based on the following sizes
        # first argloc is the frame depth and not considered for the memory
        # allocation
        # 4 bytes for the value
        # 1 byte for the type
        # 1 byte for the location
        # 1 separator byte
        # 4 bytes for the faildescr
        memsize = (len(arglocs)-1)*6+5
        datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr,
                                                    self.blocks)
        memaddr = datablockwrapper.malloc_aligned(memsize, alignment=WORD)
        datablockwrapper.done()
        mem = rffi.cast(rffi.CArrayPtr(lltype.Char), memaddr)
        i = 0
        j = 0
        while i < len(args):
            if arglocs[i+1]:
                arg = args[i]
                loc = arglocs[i+1]
                if arg.type == INT:
                    mem[j] = self.INT_TYPE
                    j += 1
                elif arg.type == REF:
                    mem[j] = self.REF_TYPE
                    j += 1
                elif arg.type == FLOAT:
                    mem[j] = self.FLOAT_TYPE
                    j += 1
                else:
                    assert 0, 'unknown type'

                if loc.is_reg() or loc.is_vfp_reg():
                    mem[j] = chr(loc.value)
                    j += 1
                elif loc.is_imm():
                    assert arg.type == INT or arg.type == REF
                    mem[j] = self.IMM_LOC
                    self.encode32(mem, j+1, loc.getint())
                    j += 5
                else:
                    mem[j] = self.STACK_LOC
                    self.encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = self.EMPTY_LOC
                j += 1
            i += 1

        mem[j] = chr(0xFF)

        n = self.cpu.get_fail_descr_number(descr)
        self.encode32(mem, j+1, n)
        self.mc.LDR_ri(r.ip.value, r.pc.value, imm=WORD)
        if save_exc:
            path = self._leave_jitted_jook_save_exc
        else:
            path = self._leave_jitted_jook
        self.mc.B(path)
        self.mc.write32(memaddr)

        return memaddr

    def align(self):
        while(self.mc.currpos() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    def gen_func_epilog(self, mc=None, cond=c.AL):
        if mc is None:
            mc = self.mc
        mc.MOV_rr(r.sp.value, r.fp.value, cond=cond)
        mc.ADD_ri(r.sp.value, r.sp.value, WORD, cond=cond)
        if self.cpu.supports_floats:
            mc.VPOP([reg.value for reg in r.callee_saved_vfp_registers])
        mc.POP([reg.value for reg in r.callee_restored_registers], cond=cond)

    def gen_func_prolog(self):
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers])
        if self.cpu.supports_floats:
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
        self.mc.SUB_ri(r.sp.value, r.sp.value,  WORD)
        self.mc.MOV_rr(r.fp.value, r.sp.value)

    def gen_bootstrap_code(self, nonfloatlocs, floatlocs, inputargs):
        for i in range(len(nonfloatlocs)):
            loc = nonfloatlocs[i]
            if loc is None:
                continue
            arg = inputargs[i]
            assert arg.type != FLOAT
            if arg.type == REF:
                addr = self.fail_boxes_ptr.get_addr_for_num(i)
            elif arg.type == INT:
                addr = self.fail_boxes_int.get_addr_for_num(i)
            else:
                assert 0
            if loc.is_reg():
                reg = loc
            else:
                reg = r.ip
            self.mc.gen_load_int(reg.value, addr)
            self.mc.LDR_ri(reg.value, reg.value)
            if loc.is_stack():
                self.mov_loc_loc(r.ip, loc)
        for i in range(len(floatlocs)):
            loc = floatlocs[i]
            if loc is None:
                continue
            arg = inputargs[i]
            assert arg.type == FLOAT
            addr = self.fail_boxes_float.get_addr_for_num(i)
            self.mc.gen_load_int(r.ip.value, addr)
            if loc.is_vfp_reg():
                self.mc.VLDR(loc.value, r.ip.value)
            else:
                tmpreg = r.d0
                with saved_registers(self.mc, [], [tmpreg]):
                    self.mc.VLDR(tmpreg.value, r.ip.value)
                    self.mov_loc_loc(tmpreg, loc)

    def _count_reg_args(self, args):
        reg_args = 0
        words = 0
        for x in range(min(len(args), 4)):
            if args[x].type == FLOAT:
                words += 2
            else:
                words += 1
            reg_args += 1
            if words > 4:
                reg_args = x
                break
        return reg_args

    def gen_direct_bootstrap_code(self, loop_head, looptoken, inputargs):
        self.gen_func_prolog()
        nonfloatlocs, floatlocs = looptoken._arm_arglocs

        reg_args = self._count_reg_args(inputargs)

        stack_locs = len(inputargs) - reg_args
        selected_reg = 0
        for i in range(reg_args):
            arg = inputargs[i]
            if arg.type == FLOAT:
                loc = floatlocs[i]
            else:
                loc = nonfloatlocs[i]
            self.mov_loc_loc(r.all_regs[selected_reg], loc)
            if inputargs[i].type == FLOAT:
                selected_reg += 2
            else:
                selected_reg += 1

        stack_position = len(r.callee_saved_registers)*WORD + \
                            len(r.callee_saved_vfp_registers)*2*WORD + \
                            WORD # for the FAIL INDEX
        for i in range(reg_args, len(inputargs)):
            arg = inputargs[i]
            if arg.type == FLOAT:
                loc = floatlocs[i]
            else:
                loc = nonfloatlocs[i]
            if loc.is_reg():
                self.mc.LDR_ri(loc.value, r.fp.value, stack_position)
            elif loc.is_vfp_reg():
                self.mc.VLDR(loc.value, r.fp.value, stack_position)
            elif loc.is_stack():
                if loc.type == FLOAT:
                    with saved_registers(self.mc, [], [r.d0]):
                        self.mc.VLDR(r.d0.value, r.fp.value, stack_position)
                        self.mov_loc_loc(r.d0, loc)
                elif loc.type == INT or loc.type == REF:
                    self.mc.LDR_ri(r.ip.value, r.fp.value, stack_position)
                    self.mov_loc_loc(r.ip, loc)
                else:
                    assert 0, 'invalid location'
            else:
                assert 0, 'invalid location'
            if loc.type == FLOAT:
                size = 2
            else:
                size = 1
            stack_position += size * WORD

        sp_patch_location = self._prepare_sp_patch_position()
        self.mc.B_offs(loop_head)
        self._patch_sp_offset(sp_patch_location, looptoken._arm_frame_depth)

    def _dump(self, ops, type='loop'):
        debug_start('jit-backend-ops')
        debug_print(type)
        for op in ops:
            debug_print(op.repr())
        debug_stop('jit-backend-ops')
    # cpu interface
    def assemble_loop(self, inputargs, operations, looptoken, log):
        self._dump(operations)
        self.setup()
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(longevity, assembler=self, frame_manager=ARMFrameManager())

        clt = CompiledLoopToken(self.cpu, looptoken.number)
        looptoken.compiled_loop_token = clt

        self.align()
        self.gen_func_prolog()
        sp_patch_location = self._prepare_sp_patch_position()
        nonfloatlocs, floatlocs = regalloc.prepare_loop(inputargs, operations, looptoken)
        self.gen_bootstrap_code(nonfloatlocs, floatlocs, inputargs)
        looptoken._arm_arglocs = [nonfloatlocs, floatlocs]
        loop_head = self.mc.currpos()

        looptoken._arm_loop_code = loop_head
        looptoken._arm_bootstrap_code = 0

        self._walk_operations(operations, regalloc)

        looptoken._arm_frame_depth = regalloc.frame_manager.frame_depth
        self._patch_sp_offset(sp_patch_location, looptoken._arm_frame_depth)

        self.align()

        direct_bootstrap_code = self.mc.currpos()
        self.gen_direct_bootstrap_code(loop_head, looptoken, inputargs)

        loop_start = self.materialize_loop(looptoken)
        looptoken._arm_bootstrap_code = loop_start
        looptoken._arm_direct_bootstrap_code = loop_start + direct_bootstrap_code
        self.update_descrs_for_bridges(loop_start)
        if log and not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(loop_start, 'loop_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling loop with token %r' % looptoken
        self.teardown()

    def assemble_bridge(self, faildescr, inputargs, operations,
                                                    original_loop_token, log):
        self._dump(operations, 'bridge')
        self.setup()
        assert isinstance(faildescr, AbstractFailDescr)
        code = faildescr._failure_recovery_code
        enc = rffi.cast(rffi.CCHARP, code)
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(longevity, assembler=self,
                                            frame_manager=ARMFrameManager())

        sp_patch_location = self._prepare_sp_patch_position()
        frame_depth = faildescr._arm_frame_depth
        locs = self.decode_inputargs(enc, inputargs, regalloc)
        regalloc.update_bindings(locs, frame_depth, inputargs)

        self._walk_operations(operations, regalloc)

        #original_loop_token._arm_frame_depth = regalloc.frame_manager.frame_depth
        self._patch_sp_offset(sp_patch_location, regalloc.frame_manager.frame_depth)

        bridge_start = self.materialize_loop(original_loop_token)
        self.update_descrs_for_bridges(bridge_start)

        self.patch_trace(faildescr, original_loop_token, bridge_start, regalloc)
        if log and not we_are_translated():
            print 'Bridge', inputargs, operations
            self.mc._dump_trace(bridge_start, 'bridge_%d.asm' %
            self.cpu.total_compiled_bridges)
        self.teardown()

    def materialize_loop(self, looptoken):
        allblocks = self.get_asmmemmgr_blocks(looptoken)
        for block in self.blocks:
            allblocks.append(block)
        return self.mc.materialize(self.cpu.asmmemmgr, allblocks,
                                   self.cpu.gc_ll_descr.gcrootmap)

    def update_descrs_for_bridges(self, block_start):
        for descr in self.guard_descrs:
            descr._arm_block_start = block_start

    def teardown(self):
        self.mc = None
        self.guard_descrs = None
        #self.looppos = -1
        #self.currently_compiling_loop = None

    def get_asmmemmgr_blocks(self, looptoken):
        clt = looptoken.compiled_loop_token
        if clt.asmmemmgr_blocks is None:
            clt.asmmemmgr_blocks = []
        return clt.asmmemmgr_blocks

    def _prepare_sp_patch_position(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update the
        sp according to the number of spilled variables"""
        size = (self.mc.size_of_gen_load_int+WORD)
        l = self.mc.currpos()
        for _ in range(size//WORD):
            self.mc.MOV_rr(r.r0.value, r.r0.value)
        return l

    def _patch_sp_offset(self, pos, frame_depth):
        cb = OverwritingBuilder(self.mc, pos, OverwritingBuilder.size_of_gen_load_int)
        # Note: the frame_depth is one less than the value stored in the frame
        # manager
        if frame_depth == 1:
            return
        n = (frame_depth)*WORD
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
        fcond=c.AL
        while regalloc.position() < len(operations) - 1:
            regalloc.next_instruction()
            i = regalloc.position()
            op = operations[i]
            opnum = op.getopnum()
            if op.has_no_side_effect() and op.result not in regalloc.longevity:
                regalloc.possibly_free_vars_for_op(op)
            elif self.can_merge_with_next_guard(op, i, operations):
                regalloc.next_instruction()
                arglocs = regalloc.operations_with_guard[opnum](regalloc, op,
                                        operations[i+1], fcond)
                fcond = self.operations_with_guard[opnum](self, op,
                                        operations[i+1], arglocs, regalloc, fcond)
            else:
                arglocs = regalloc.operations[opnum](regalloc, op, fcond)
                fcond = self.operations[opnum](self, op, arglocs, regalloc, fcond)
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc._check_invariants()

    def can_merge_with_next_guard(self, op, i, operations):
        if op.getopnum() == rop.CALL_MAY_FORCE or op.getopnum() == rop.CALL_ASSEMBLER:
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if op.getopnum() == rop.INT_MUL_OVF:
            opnum = operations[i + 1].getopnum()
            assert opnum  == rop.GUARD_OVERFLOW or opnum == rop.GUARD_NO_OVERFLOW
            return True
        return False


    def _ensure_result_bit_extension(self, resloc, size, signed):
        if size == 4:
            return
        if size == 1:
            if not signed: #unsigned char
                self.mc.AND_ri(resloc.value, resloc.value, 0xFF)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 24)
                self.mc.ASR_ri(resloc.value, resloc.value, 24)
        elif size == 2:
            if not signed:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.LSR_ri(resloc.value, resloc.value, 16)
                #self.mc.MOV_ri(r.ip.value, 0xFF)
                #self.mc.ORR_ri(r.ip.value, 0xCFF)
                #self.mc.AND_rr(resloc.value, resloc.value, r.ip.value)
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

    # XXX needs float support
    def regalloc_mov(self, prev_loc, loc, cond=c.AL):
        if prev_loc.is_imm():
            if loc.is_reg():
                new_loc = loc
            else:
                assert loc is not r.ip
                new_loc = r.ip
            if _check_imm_arg(ConstInt(prev_loc.getint())):
                self.mc.MOV_ri(new_loc.value, prev_loc.getint(), cond=cond)
            else:
                self.mc.gen_load_int(new_loc.value, prev_loc.getint(), cond=cond)
            prev_loc = new_loc
            if not loc.is_stack():
                return
        if prev_loc.is_imm_float():
            temp = r.lr
            self.mc.gen_load_int(temp.value, prev_loc.getint())
            if loc.is_reg():
                # we need to load one word to loc and one to loc+1 which are
                # two 32-bit core registers
                self.mc.LDR_ri(loc.value, temp.value)
                self.mc.LDR_ri(loc.value+1, temp.value, imm=WORD)
            elif loc.is_vfp_reg():
                # we need to load the thing into loc, which is a vfp reg
                self.mc.VLDR(loc.value, temp.value)
            assert not loc.is_stack()
            return
        if loc.is_stack() or prev_loc.is_stack():
            temp = r.lr
            if loc.is_stack() and prev_loc.is_reg():
                offset = ConstInt(loc.position*-WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.STR_rr(prev_loc.value, r.fp.value, temp.value, cond=cond)
                else:
                    self.mc.STR_ri(prev_loc.value, r.fp.value, offset.value, cond=cond)
            elif loc.is_reg() and prev_loc.is_stack():
                offset = ConstInt(prev_loc.position*-WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.LDR_rr(loc.value, r.fp.value, temp.value, cond=cond)
                else:
                    self.mc.LDR_ri(loc.value, r.fp.value, offset.value, cond=cond)
            elif loc.is_stack() and prev_loc.is_vfp_reg():
                # spill vfp register
                offset = ConstInt(loc.position*-WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.ADD_rr(temp.value, r.fp.value, temp.value)
                else:
                    self.mc.ADD_rr(temp.value, r.fp.value, offset)
                self.mc.VSTR(prev_loc.value, temp.value, cond=cond)
            elif loc.is_vfp_reg() and prev_loc.is_stack():
                # load spilled value into vfp reg
                offset = ConstInt(prev_loc.position*-WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.ADD_rr(temp.value, r.fp.value, temp.value)
                else:
                    self.mc.ADD_rr(temp.value, r.fp.value, offset)
                self.mc.VLDR(loc.value, temp.value, cond=cond)
            else:
                assert 0, 'unsupported case'
        elif loc.is_reg() and prev_loc.is_reg():
            self.mc.MOV_rr(loc.value, prev_loc.value, cond=cond)
        elif loc.is_reg() and prev_loc.is_vfp_reg():
            self.mc.VMOV_rc(loc.value, loc.value+1, prev_loc.value, cond=cond)
        elif loc.is_vfp_reg() and prev_loc.is_reg():
            self.mc.VMOV_cr(loc.value, prev_loc.value, prev_loc.value+1, cond=cond)
        elif loc.is_vfp_reg() and prev_loc.is_vfp_reg():
            self.mc.VMOV_cc(loc.value, prev_loc.value, cond=cond)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def regalloc_push(self, loc):
        if loc.is_stack():
            self.regalloc_mov(loc, r.ip)
            self.mc.PUSH([r.ip.value])
        elif loc.is_reg():
            self.mc.PUSH([loc.value])
        elif loc.is_vfp_reg():
            self.mc.VPUSH([loc.value])
        elif loc.is_imm():
            self.regalloc_mov(loc, r.ip)
            self.mc.PUSH([r.ip.value])
        else:
            assert 0, 'ffuu'

    def regalloc_pop(self, loc):
        if loc.is_stack():
            self.mc.POP([r.ip.value])
            self.regalloc_mov(r.ip, loc)
        elif loc.is_reg():
            self.mc.POP([loc.value])
        elif loc.is_vfp_reg():
            self.mc.VPOP([loc.value])
        else:
            assert 0, 'ffuu'

    def leave_jitted_hook(self):
        pass

def make_operation_list():
    def notimplemented(self, op, arglocs, regalloc, fcond):
        raise NotImplementedError, op

    operations = [None] * (rop._LAST+1)
    for key, value in rop.__dict__.items():
        key = key.lower()
        if key.startswith('_'):
            continue
        methname = 'emit_op_%s' % key
        if hasattr(AssemblerARM, methname):
            func = getattr(AssemblerARM, methname).im_func
        else:
            func = notimplemented
        operations[value] = func
    return operations

def make_guard_operation_list():
    def notimplemented(self, op, guard_op, arglocs, regalloc, fcond):
        raise NotImplementedError, op
    guard_operations = [notimplemented] * rop._LAST
    for key, value in rop.__dict__.items():
        key = key.lower()
        if key.startswith('_'):
            continue
        methname = 'emit_guard_%s' % key
        if hasattr(AssemblerARM, methname):
            func = getattr(AssemblerARM, methname).im_func
            guard_operations[value] = func
    return guard_operations

AssemblerARM.operations = make_operation_list()
AssemblerARM.operations_with_guard = make_guard_operation_list()
