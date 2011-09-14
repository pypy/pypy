from __future__ import with_statement
from pypy.jit.backend.arm.helper.assembler import saved_registers, count_reg_args, \
                                                    decode32, encode32, \
                                                    decode64, encode64
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, FUNC_ALIGN, PC_OFFSET, N_REGISTERS_SAVED_BY_MALLOC
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, OverwritingBuilder
from pypy.jit.backend.arm.regalloc import (Regalloc, ARMFrameManager, ARMv7RegisterMananger,
                                                    _check_imm_arg, TempInt, TempPtr)
from pypy.jit.backend.arm.jump import remap_frame_layout
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity, TempBox
from pypy.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from pypy.jit.backend.model import CompiledLoopToken
from pypy.jit.codewriter import longlong
from pypy.jit.metainterp.history import (Const, ConstInt, ConstPtr,
                                        BoxInt, BoxPtr, AbstractFailDescr,
                                        INT, REF, FLOAT)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.rarithmetic import r_uint, r_longlong
from pypy.rlib.longlong2float import float2longlong, longlong2float
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.jit.backend.arm.opassembler import ResOpAssembler, GuardToken
from pypy.rlib.debug import (debug_print, debug_start, debug_stop,
                             have_debug_prints)

# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array, memcpy_fn

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
        self.pending_guards = None
        self._exit_code_addr = 0
        self.current_clt = None
        self.malloc_slowpath = 0
        self._regalloc = None
        self.datablockwrapper = None

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
        return operations

    def teardown(self):
        self.current_clt = None
        self._regalloc = None
        self.mc = None
        self.pending_guards = None

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
        if gc_ll_descr.get_malloc_slowpath_addr is not None:
            self._build_malloc_slowpath()
        if gc_ll_descr.gcrootmap and gc_ll_descr.gcrootmap.is_shadow_stack:
            self._build_release_gil(gc_ll_descr.gcrootmap)
        self.memcpy_addr = self.cpu.cast_ptr_to_int(memcpy_fn)
        self._exit_code_addr = self._gen_exit_path()
        self._leave_jitted_hook_save_exc = self._gen_leave_jitted_hook_code(True)
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
        self.releasegil_addr  = rffi.cast(lltype.Signed, releasegil_func)
        self.reacqgil_addr = rffi.cast(lltype.Signed, reacqgil_func)

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
        #XXX check if units are correct here, when comparing words and bytes and stuff
        # assert 0, 'check if units are correct here, when comparing words and bytes and stuff'

        enc = rffi.cast(rffi.CCHARP, mem_loc)
        frame_depth = frame_loc - (regs_loc + len(r.all_regs)*WORD + len(r.all_vfp_regs)*2*WORD)
        assert (frame_loc - frame_depth) % 4 == 0
        stack = rffi.cast(rffi.CCHARP, frame_loc - frame_depth)
        assert regs_loc % 4 == 0
        vfp_regs = rffi.cast(rffi.CCHARP, regs_loc)
        assert (regs_loc + len(r.all_vfp_regs)*2*WORD) % 4 == 0
        assert frame_depth >= 0

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
                # imm value
                if group == self.INT_TYPE or group == self.REF_TYPE:
                    value = decode32(enc, i+1)
                    i += 4
                else:
                    assert group == self.FLOAT_TYPE
                    adr = decode32(enc, i+1)
                    value = rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0]
                    self.fail_boxes_float.setitem(fail_index, value)
                    i += 4
                    continue
            elif res == self.STACK_LOC:
                stack_loc = decode32(enc, i+1)
                i += 4
                if group == self.FLOAT_TYPE:
                    value = decode64(stack, frame_depth - stack_loc*WORD)
                    self.fail_boxes_float.setitem(fail_index, value)
                    continue
                else:
                    value = decode32(stack, frame_depth - stack_loc*WORD)
            else: # REG_LOC
                reg = ord(enc[i])
                if group == self.FLOAT_TYPE:
                    value = decode64(vfp_regs, reg*2*WORD)
                    self.fail_boxes_float.setitem(fail_index, value)
                    continue
                else:
                    value = decode32(regs, reg*WORD)

            if group == self.INT_TYPE:
                self.fail_boxes_int.setitem(fail_index, value)
            elif group == self.REF_TYPE:
                tgt = self.fail_boxes_ptr.get_addr_for_num(fail_index)
                rffi.cast(rffi.LONGP, tgt)[0] = value
            else:
                assert 0, 'unknown type'


        assert enc[i] == self.END_OF_LOCS
        descr = decode32(enc, i+1)
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
                stack_loc = decode32(enc, j+1)
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

    def _build_malloc_slowpath(self):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        mc = ARMv7Builder()
        assert self.cpu.supports_floats
        # We need to push two registers here because we are goin to make a
        # call an therefore the stack needs to be 8-byte aligned
        mc.PUSH([r.ip.value, r.lr.value])
        with saved_registers(mc, [], r.all_vfp_regs):
            # At this point we know that the values we need to compute the size
            # are stored in r0 and r1.
            mc.SUB_rr(r.r0.value, r.r1.value, r.r0.value)
            addr = self.cpu.gc_ll_descr.get_malloc_slowpath_addr()
            # XXX replace with an STMxx operation
            for reg, ofs in ARMv7RegisterMananger.REGLOC_TO_COPY_AREA_OFS.items():
                mc.STR_ri(reg.value, r.fp.value, imm=ofs)
            mc.BL(addr)
            for reg, ofs in ARMv7RegisterMananger.REGLOC_TO_COPY_AREA_OFS.items():
                mc.LDR_ri(reg.value, r.fp.value, imm=ofs)
        nursery_free_adr = self.cpu.gc_ll_descr.get_nursery_free_addr()
        mc.gen_load_int(r.r1.value, nursery_free_adr)
        mc.LDR_ri(r.r1.value, r.r1.value)
        # see above
        mc.POP([r.ip.value, r.pc.value])
        rawstart = mc.materialize(self.cpu.asmmemmgr, [])
        self.malloc_slowpath = rawstart

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
        
        self._insert_checks(mc)
        with saved_registers(mc, r.all_regs, r.all_vfp_regs):
            mc.MOV_rr(r.r0.value, r.ip.value) # move mem block address, to r0 to pass as
            mc.MOV_rr(r.r1.value, r.fp.value) # pass the current frame pointer as second param
            mc.MOV_rr(r.r2.value, r.sp.value) # pass the current stack pointer as third param
            self._insert_checks(mc)
            mc.BL(rffi.cast(lltype.Signed, decode_registers_addr))
            mc.MOV_rr(r.ip.value, r.r0.value)
        mc.MOV_rr(r.r0.value, r.ip.value)
        self.gen_func_epilog(mc=mc)
        return mc.materialize(self.cpu.asmmemmgr, [],
                                   self.cpu.gc_ll_descr.gcrootmap)

    def gen_descr_encoding(self, descr, args, arglocs):
        # The size of the allocated memory is based on the following sizes
        # first argloc is the frame depth and not considered for the memory
        # allocation
        # 4 bytes for the value
        # 1 byte for the type
        # 1 byte for the location
        # 1 separator byte
        # 4 bytes for the faildescr
        # const floats are stored in memory and the box contains the address
        memsize = (len(arglocs)-1)*6+5
        memaddr = self.datablockwrapper.malloc_aligned(memsize, alignment=1)
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
                elif loc.is_imm() or loc.is_imm_float():
                    assert (arg.type == INT or arg.type == REF
                                or arg.type == FLOAT)
                    mem[j] = self.IMM_LOC
                    encode32(mem, j+1, loc.getint())
                    j += 5
                else:
                    assert loc.is_stack()
                    mem[j] = self.STACK_LOC
                    encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = self.EMPTY_LOC
                j += 1
            i += 1

        mem[j] = chr(0xFF)

        n = self.cpu.get_fail_descr_number(descr)
        encode32(mem, j+1, n)
        return memaddr

    def _gen_path_to_exit_path(self, descr, args, arglocs, fcond=c.AL, save_exc=False):
        memaddr = self.gen_descr_encoding(descr, args, arglocs)
        self.gen_exit_code(self.mc, memaddr, fcond, save_exc)
        return memaddr

    def gen_exit_code(self, mc, memaddr, fcond=c.AL, save_exc=False):
        self.mc.gen_load_int(r.ip.value, memaddr)
        #mc.LDR_ri(r.ip.value, r.pc.value, imm=WORD)
        if save_exc:
            path = self._leave_jitted_hook_save_exc
        else:
            path = self._leave_jitted_hook
        mc.B(path)
        #mc.write32(memaddr)

    def align(self):
        while(self.mc.currpos() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    def gen_func_epilog(self, mc=None, cond=c.AL):
        gcrootmap = self.cpu.gc_ll_descr.gcrootmap
        if mc is None:
            mc = self.mc
        if gcrootmap and gcrootmap.is_shadow_stack:
            self.gen_footer_shadowstack(gcrootmap, mc)
        offset = 1
        if self.cpu.supports_floats:
            offset += 1 # to keep stack alignment
        mc.MOV_rr(r.sp.value, r.fp.value, cond=cond)
        mc.ADD_ri(r.sp.value, r.sp.value, (N_REGISTERS_SAVED_BY_MALLOC+offset)*WORD, cond=cond)
        if self.cpu.supports_floats:
            mc.VPOP([reg.value for reg in r.callee_saved_vfp_registers], cond=cond)
        mc.POP([reg.value for reg in r.callee_restored_registers], cond=cond)

    def gen_func_prolog(self):
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers])
        offset = 1
        if self.cpu.supports_floats:
            self.mc.VPUSH([reg.value for reg in r.callee_saved_vfp_registers])
            offset +=1 # to keep stack alignment
        # here we modify the stack pointer to leave room for the 9 registers
        # that are going to be saved here around malloc calls and one word to
        # store the force index
        self.mc.SUB_ri(r.sp.value, r.sp.value, (N_REGISTERS_SAVED_BY_MALLOC+offset)*WORD)
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
        self.mc.LDR_ri(r.r4.value, r.ip.value) # LDR r4, [rootstacktop]
        self.mc.ADD_ri(r.r5.value, r.r4.value, imm=2*WORD) # ADD r5, r4 [2*WORD]
        self.mc.gen_load_int(r.r6.value, gcrootmap.MARKER)
        self.mc.STR_ri(r.r6.value, r.r4.value)
        self.mc.STR_ri(r.fp.value, r.r4.value, WORD) 
        self.mc.STR_ri(r.r5.value, r.ip.value)

    def gen_footer_shadowstack(self, gcrootmap, mc):
        rst = gcrootmap.get_root_stack_top_addr()
        mc.gen_load_int(r.ip.value, rst)
        mc.LDR_ri(r.r4.value, r.ip.value) # LDR r4, [rootstacktop]
        mc.SUB_ri(r.r5.value, r.r4.value, imm=2*WORD) # ADD r5, r4 [2*WORD]
        mc.STR_ri(r.r5.value, r.ip.value)

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
                self.mc.VLDR(r.vfp_ip.value, r.ip.value)
                self.mov_loc_loc(r.vfp_ip, loc)

    def gen_direct_bootstrap_code(self, loop_head, looptoken, inputargs):
        self.gen_func_prolog()
        nonfloatlocs, floatlocs = looptoken._arm_arglocs

        reg_args = count_reg_args(inputargs)

        stack_locs = len(inputargs) - reg_args

        selected_reg = 0
        count = 0
        float_args = []
        nonfloat_args = []
        nonfloat_regs = []
        # load reg args
        for i in range(reg_args):
            arg = inputargs[i]
            if arg.type == FLOAT and count % 2 != 0:
                    selected_reg += 1
                    count = 0
            reg = r.all_regs[selected_reg]

            if arg.type == FLOAT:
                float_args.append((reg, floatlocs[i]))
            else:
                nonfloat_args.append(reg)
                nonfloat_regs.append(nonfloatlocs[i])

            if arg.type == FLOAT:
                selected_reg += 2
            else:
                selected_reg += 1
                count += 1

        # move float arguments to vfp regsiters
        for loc, vfp_reg in float_args:
            self.mov_to_vfp_loc(loc, r.all_regs[loc.value+1], vfp_reg)

        # remap values stored in core registers
        remap_frame_layout(self, nonfloat_args, nonfloat_regs, r.ip)

        # load values passed on the stack to the corresponding locations
        stack_position = len(r.callee_saved_registers)*WORD + \
                            len(r.callee_saved_vfp_registers)*2*WORD + \
                            N_REGISTERS_SAVED_BY_MALLOC * WORD + \
                            2 * WORD # for the FAIL INDEX and the stack padding
        count = 0
        for i in range(reg_args, len(inputargs)):
            arg = inputargs[i]
            if arg.type == FLOAT:
                loc = floatlocs[i]
            else:
                loc = nonfloatlocs[i]
            if loc.is_reg():
                self.mc.LDR_ri(loc.value, r.fp.value, stack_position)
                count += 1
            elif loc.is_vfp_reg():
                if count % 2 != 0:
                    stack_position += WORD
                    count = 0
                self.mc.VLDR(loc.value, r.fp.value, stack_position)
            elif loc.is_stack():
                if loc.type == FLOAT:
                    if count % 2 != 0:
                        stack_position += WORD
                        count = 0
                    self.mc.VLDR(r.vfp_ip.value, r.fp.value, stack_position)
                    self.mov_loc_loc(r.vfp_ip, loc)
                elif loc.type == INT or loc.type == REF:
                    count += 1
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

        clt = CompiledLoopToken(self.cpu, looptoken.number)
        clt.allgcrefs = []
        looptoken.compiled_loop_token = clt

        operations = self.setup(looptoken, operations)
        self._dump(operations)
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = Regalloc(longevity, assembler=self, frame_manager=ARMFrameManager())


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

        self.write_pending_failure_recoveries()
        loop_start = self.materialize_loop(looptoken)
        looptoken._arm_bootstrap_code = loop_start
        looptoken._arm_direct_bootstrap_code = loop_start + direct_bootstrap_code
        self.process_pending_guards(loop_start)
        if log and not we_are_translated():
            print 'Loop', inputargs, operations
            self.mc._dump_trace(loop_start, 'loop_%s.asm' % self.cpu.total_compiled_loops)
            print 'Done assembling loop with token %r' % looptoken
        self.teardown()

    def assemble_bridge(self, faildescr, inputargs, operations,
                                                    original_loop_token, log):
        operations = self.setup(original_loop_token, operations)
        self._dump(operations, 'bridge')
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

        self.write_pending_failure_recoveries()
        bridge_start = self.materialize_loop(original_loop_token)
        self.process_pending_guards(bridge_start)

        self.patch_trace(faildescr, original_loop_token, bridge_start, regalloc)
        if log and not we_are_translated():
            print 'Bridge', inputargs, operations
            self.mc._dump_trace(bridge_start, 'bridge_%d.asm' %
            self.cpu.total_compiled_bridges)
        self.teardown()

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

            memaddr = self._gen_path_to_exit_path(descr, tok.failargs,
                                            tok.faillocs, save_exc=tok.save_exc)
            # store info on the descr
            descr._arm_frame_depth = tok.faillocs[0].getint()
            descr._failure_recovery_code = memaddr
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
                # overwrite the generate NOP with a B_offs to the pos of the stub
                mc = ARMv7Builder()
                mc.B_offs(descr._arm_guard_pos - tok.offset, c.get_opposite_of(tok.fcond))
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
        """Generate NOPs as placeholder to patch the instruction(s) to update the
        sp according to the number of spilled variables"""
        size = (self.mc.size_of_gen_load_int+WORD)
        l = self.mc.currpos()
        for _ in range(size//WORD):
            self.mc.NOP()
        return l

    def _patch_sp_offset(self, pos, frame_depth):
        cb = OverwritingBuilder(self.mc, pos, OverwritingBuilder.size_of_gen_load_int)
        # Note: the frame_depth is one less than the value stored in the frame
        # manager
        if frame_depth == 1:
            return
        n = (frame_depth-1)*WORD

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
        fcond=c.AL
        self._regalloc = regalloc
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
            elif not we_are_translated() and op.getopnum() == -124:
                regalloc.prepare_force_spill(op, fcond)
            else:
                arglocs = regalloc.operations[opnum](regalloc, op, fcond)
                if arglocs is not None:
                    fcond = self.operations[opnum](self, op, arglocs, regalloc, fcond)
            if op.result:
                regalloc.possibly_free_var(op.result)
            regalloc.possibly_free_vars_for_op(op)
            regalloc._check_invariants()

    def can_merge_with_next_guard(self, op, i, operations):
        num = op.getopnum()
        if num == rop.CALL_MAY_FORCE or num == rop.CALL_ASSEMBLER:
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if num == rop.INT_MUL_OVF or num == rop.INT_ADD_OVF or num == rop.INT_SUB_OVF:
            opnum = operations[i + 1].getopnum()
            assert opnum  == rop.GUARD_OVERFLOW or opnum == rop.GUARD_NO_OVERFLOW
            return True
        if num == rop.CALL_RELEASE_GIL:
            return True
        return False


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

    def regalloc_mov(self, prev_loc, loc, cond=c.AL):
        # really XXX add tests
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
            assert loc.is_vfp_reg()
            temp = r.lr
            self.mc.gen_load_int(temp.value, prev_loc.getint())
            self.mc.VLDR(loc.value, temp.value)
            return
        if loc.is_stack() or prev_loc.is_stack():
            temp = r.lr
            if loc.is_stack() and prev_loc.is_reg():
                # spill a core register
                offset = ConstInt(loc.position*WORD)
                if not _check_imm_arg(offset, size=0xFFF):
                    self.mc.gen_load_int(temp.value, -offset.value)
                    self.mc.STR_rr(prev_loc.value, r.fp.value, temp.value, cond=cond)
                else:
                    self.mc.STR_ri(prev_loc.value, r.fp.value, imm=-1*offset.value, cond=cond)
            elif loc.is_reg() and prev_loc.is_stack():
                # unspill a core register
                offset = ConstInt(prev_loc.position*WORD)
                if not _check_imm_arg(offset, size=0xFFF):
                    self.mc.gen_load_int(temp.value, -offset.value)
                    self.mc.LDR_rr(loc.value, r.fp.value, temp.value, cond=cond)
                else:
                    self.mc.LDR_ri(loc.value, r.fp.value, imm=-offset.value, cond=cond)
            elif loc.is_stack() and prev_loc.is_vfp_reg():
                # spill vfp register
                offset = ConstInt(loc.position*WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.SUB_rr(temp.value, r.fp.value, temp.value)
                else:
                    self.mc.SUB_ri(temp.value, r.fp.value, offset.value)
                self.mc.VSTR(prev_loc.value, temp.value, cond=cond)
            elif loc.is_vfp_reg() and prev_loc.is_stack():
                # load spilled value into vfp reg
                offset = ConstInt(prev_loc.position*WORD)
                if not _check_imm_arg(offset):
                    self.mc.gen_load_int(temp.value, offset.value)
                    self.mc.SUB_rr(temp.value, r.fp.value, temp.value)
                else:
                    self.mc.SUB_ri(temp.value, r.fp.value, offset.value)
                self.mc.VLDR(loc.value, temp.value, cond=cond)
            else:
                assert 0, 'unsupported case'
        elif loc.is_reg() and prev_loc.is_reg():
            self.mc.MOV_rr(loc.value, prev_loc.value, cond=cond)
        elif loc.is_vfp_reg() and prev_loc.is_vfp_reg():
            self.mc.VMOV_cc(loc.value, prev_loc.value, cond=cond)
        else:
            assert 0, 'unsupported case'
    mov_loc_loc = regalloc_mov

    def mov_from_vfp_loc(self, vfp_loc, reg1, reg2, cond=c.AL):
        assert reg1.value + 1 == reg2.value
        temp = r.lr
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_rc(reg1.value, reg2.value, vfp_loc.value, cond=cond)
        elif vfp_loc.is_imm_float():
            self.mc.gen_load_int(temp.value, vfp_loc.getint(), cond=cond)
            # we need to load one word to loc and one to loc+1 which are
            # two 32-bit core registers
            self.mc.LDR_ri(reg1.value, temp.value, cond=cond)
            self.mc.LDR_ri(reg2.value, temp.value, imm=WORD, cond=cond)
        elif vfp_loc.is_stack():
            # load spilled value into vfp reg
            offset = ConstInt((vfp_loc.position)*WORD)
            if not _check_imm_arg(offset, size=0xFFF):
                self.mc.gen_load_int(temp.value, -offset.value, cond=cond)
                self.mc.LDR_rr(reg1.value, r.fp.value, temp.value, cond=cond)
                self.mc.ADD_ri(temp.value, temp.value, imm=WORD, cond=cond)
                self.mc.LDR_rr(reg2.value, r.fp.value, temp.value, cond=cond)
            else:
                self.mc.LDR_ri(reg1.value, r.fp.value, imm=-offset.value, cond=cond)
                self.mc.LDR_ri(reg2.value, r.fp.value, imm=-offset.value+WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def mov_to_vfp_loc(self, reg1, reg2, vfp_loc, cond=c.AL):
        assert reg1.value + 1 == reg2.value
        temp = r.lr
        if vfp_loc.is_vfp_reg():
            self.mc.VMOV_cr(vfp_loc.value, reg1.value, reg2.value, cond=cond)
        elif vfp_loc.is_stack():
            # load spilled value into vfp reg
            offset = ConstInt((vfp_loc.position)*WORD)
            if not _check_imm_arg(offset, size=0xFFF):
                self.mc.gen_load_int(temp.value, -offset.value, cond=cond)
                self.mc.STR_rr(reg1.value, r.fp.value, temp.value, cond=cond)
                self.mc.ADD_ri(temp.value, temp.value, imm=WORD, cond=cond)
                self.mc.STR_rr(reg2.value, r.fp.value, temp.value, cond=cond)
            else:
                self.mc.STR_ri(reg1.value, r.fp.value, imm=-offset.value, cond=cond)
                self.mc.STR_ri(reg2.value, r.fp.value, imm=-offset.value+WORD, cond=cond)
        else:
            assert 0, 'unsupported case'

    def regalloc_push(self, loc):
        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_mov(loc, scratch_reg)
            self.regalloc_push(scratch_reg)
        elif loc.is_reg():
            self.mc.PUSH([loc.value])
        elif loc.is_vfp_reg():
            self.mc.VPUSH([loc.value])
        elif loc.is_imm():
            self.regalloc_mov(loc, r.ip)
            self.mc.PUSH([r.ip.value])
        elif loc.is_imm_float():
            self.regalloc_mov(loc, r.d15)
            self.mc.VPUSH([r.d15.value])
        else:
            assert 0, 'ffuu'

    def regalloc_pop(self, loc):
        if loc.is_stack():
            if loc.type != FLOAT:
                scratch_reg = r.ip
            else:
                scratch_reg = r.vfp_ip
            self.regalloc_pop(scratch_reg)
            self.regalloc_mov(scratch_reg, loc)
        elif loc.is_reg():
            self.mc.POP([loc.value])
        elif loc.is_vfp_reg():
            self.mc.VPOP([loc.value])
        else:
            assert 0, 'ffuu'

    def leave_jitted_hook(self):
        ptrs = self.fail_boxes_ptr.ar
        llop.gc_assume_young_pointers(lltype.Void,
                                      llmemory.cast_ptr_to_adr(ptrs))

    def malloc_cond(self, nursery_free_adr, nursery_top_adr, size, tid):
        size = max(size, self.cpu.gc_ll_descr.minimal_size_in_nursery)
        size = (size + WORD-1) & ~(WORD-1)     # round up

        self.mc.gen_load_int(r.r0.value, nursery_free_adr)
        self.mc.LDR_ri(r.r0.value, r.r0.value)

        if _check_imm_arg(ConstInt(size)):
            self.mc.ADD_ri(r.r1.value, r.r0.value, size)
        else:
            self.mc.gen_load_int(r.r1.value, size)
            self.mc.ADD_rr(r.r1.value, r.r0.value, r.r1.value)

        # XXX maybe use an offset from the value nursery_free_addr
        self.mc.gen_load_int(r.ip.value, nursery_top_adr)
        self.mc.LDR_ri(r.ip.value, r.ip.value)

        self.mc.CMP_rr(r.r1.value, r.ip.value)

        fast_jmp_pos = self.mc.currpos()
        self.mc.NOP()

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
        self.mc.BL(self.malloc_slowpath)

        offset = self.mc.currpos() - fast_jmp_pos
        pmc = OverwritingBuilder(self.mc, fast_jmp_pos, WORD)
        pmc.ADD_ri(r.pc.value, r.pc.value, offset - PC_OFFSET, cond=c.LS)

        self.mc.gen_load_int(r.ip.value, nursery_free_adr)
        self.mc.STR_ri(r.r1.value, r.ip.value)

        self.mc.gen_load_int(r.ip.value, tid)
        self.mc.STR_ri(r.ip.value, r.r0.value)


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
