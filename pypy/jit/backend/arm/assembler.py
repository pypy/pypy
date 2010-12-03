from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, FUNC_ALIGN, PC_OFFSET
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, ARMv7InMemoryBuilder
from pypy.jit.backend.arm.regalloc import ARMRegisterManager, ARMFrameManager
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity, TempBox
from pypy.jit.metainterp.history import (Const, ConstInt, BoxInt, AbstractFailDescr,
                                                INT, REF, FLOAT)
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.jit.backend.arm.opassembler import ResOpAssembler

# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

class AssemblerARM(ResOpAssembler):

    def __init__(self, cpu, failargs_limit=1000):
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self.fail_boxes_ptr = values_array(llmemory.GCREF, failargs_limit)
        self.setup_failure_recovery()
        self._debug_asm = True
        self.mc = None
        self.malloc_func_addr = 0
        self.malloc_array_func_addr = 0
        self.malloc_str_func_addr = 0
        self.malloc_unicode_func_addr = 0
        self.memcpy_addr = 0

    def setup_mc(self):
        self.mc = ARMv7Builder()
        self._exit_code_addr = self.mc.curraddr()
        self._gen_exit_path()
        self.align()
        self.mc._start_addr = self.mc.curraddr()

    def setup(self):
        if self.mc is None:
            self.setup_mc()

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
        frame_depth = frame_loc - (regs_loc + len(r.all_regs)*WORD)
        stack = rffi.cast(rffi.CCHARP, frame_loc - frame_depth)
        regs = rffi.cast(rffi.CCHARP, regs_loc)
        i = -1
        fail_index = -1
        if self.debug:
            import pdb; pdb.set_trace()
        while(True):
            i += 1
            fail_index += 1
            res = enc[i]
            if res == '\xFF':
                break
            if res == '\xFE':
                continue

            group = res
            i += 1
            res = enc[i]
            if res == '\xFD':
                assert group == '\xEF'
                # imm value
                value = self.decode32(enc, i+1)
                i += 4
            elif res == '\xFC': # stack location
                stack_loc = self.decode32(enc, i+1)
                value = self.decode32(stack, frame_depth - stack_loc*WORD)
                i += 4
            else: # an int in a reg location
                reg = ord(enc[i])
                value = self.decode32(regs, reg*WORD)

            if group == '\xEF': # INT
                self.fail_boxes_int.setitem(fail_index, value)
            elif group == '\xEE': # REF
                self.fail_boxes_ptr.setitem(fail_index, rffi.cast(llmemory.GCREF, value))
            else:
                assert 0, 'unknown type'


        assert enc[i] == '\xFF'
        descr = self.decode32(enc, i+1)
        self.fail_boxes_count = fail_index
        return descr

    def decode_inputargs(self, enc, inputargs, regalloc):
        locs = []
        j = 0
        for i in range(len(inputargs)):
            res = enc[j]
            if res == '\xFF':
                assert 0, 'reached end of encoded area'
            # XXX decode imm and and stack locs and REFs
            while res == '\xFE':
                j += 1
                res = enc[j]

            assert res == '\xEF' # only int location for now
            j += 1
            res = enc[j]
            if res == '\xFD': # imm location
                assert 0, 'fail'
            elif res == '\xFC': # stack location
                stack_loc = self.decode32(enc, j+1)
                loc = regalloc.frame_manager.frame_pos(stack_loc, INT)
                j += 4
            else: # reg location
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

    def encode32(self, mem, i, n):
        mem[i] = chr(n & 0xFF)
        mem[i+1] = chr((n >> 8) & 0xFF)
        mem[i+2] = chr((n >> 16) & 0xFF)
        mem[i+3] = chr((n >> 24) & 0xFF)

    def _gen_exit_path(self):
        decode_registers_addr = llhelper(self.recovery_func_sign, self.failure_recovery_func)

        self.mc.PUSH([reg.value for reg in r.all_regs])     # registers r0 .. r10
        self.mc.MOV_rr(r.r0.value, r.lr.value) # move mem block address, to r0 to pass as
        self.mc.MOV_rr(r.r1.value, r.fp.value) # pass the current frame pointer as second param
        self.mc.MOV_rr(r.r2.value, r.sp.value) # pass the current stack pointer as third param

        self.mc.BL(rffi.cast(lltype.Signed, decode_registers_addr))
        self.mc.MOV_rr(r.ip.value, r.r0.value)
        self.mc.POP([reg.value for reg in r.all_regs])
        self.mc.MOV_rr(r.r0.value, r.ip.value)
        self.mc.ensure_can_fit(self.epilog_size)
        self.gen_func_epilog()

    def _gen_path_to_exit_path(self, op, args, regalloc, fcond=c.AL):
        """
        types:
        \xEE = REF
        \xEF = INT
        location:
        \xFC = stack location
        \xFD = imm location
        emtpy = reg location
        \xFE = Empty arg
        """

        descr = op.getdescr()
        if op.getopnum() != rop.FINISH:
            assert isinstance(descr, AbstractFailDescr)
            descr._arm_frame_depth = regalloc.frame_manager.frame_depth
        reg = r.lr
        # XXX free this memory
        # XXX allocate correct amount of memory
        mem = lltype.malloc(rffi.CArray(lltype.Char), len(args)*6+5,
                                    flavor='raw', track_allocation=False)
        i = 0
        j = 0
        while(i < len(args)):
            if args[i]:
                loc = regalloc.loc(args[i])
                if args[i].type == INT:
                    mem[j] = '\xEF'
                    j += 1
                elif args[i].type == REF:
                    mem[j] = '\xEE'
                    j += 1
                else:
                    assert 0, 'unknown type'

                if loc.is_reg():
                    mem[j] = chr(loc.value)
                    j += 1
                elif loc.is_imm():
                    assert args[i].type == INT
                    mem[j] = '\xFD'
                    self.encode32(mem, j+1, loc.getint())
                    j += 5
                else:
                    mem[j] = '\xFC'
                    self.encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = '\xFE'
                j += 1
            i += 1

        mem[j] = chr(0xFF)
        memaddr = rffi.cast(lltype.Signed, mem)

        n = self.cpu.get_fail_descr_number(descr)
        self.encode32(mem, j+1, n)
        self.mc.ensure_can_fit(4*WORD)
        self.mc.LDR_ri(r.lr.value, r.pc.value, imm=WORD)
        self.mc.B(self._exit_code_addr)
        self.mc.write32(memaddr)

        return memaddr

    def align(self):
        while(self.mc.curraddr() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    epilog_size = 3*WORD
    def gen_func_epilog(self,cond=c.AL):
        self.mc.MOV_rr(r.sp.value, r.fp.value)
        self.mc.ADD_ri(r.sp.value, r.sp.value, WORD)
        self.mc.POP([reg.value for reg in r.callee_restored_registers], cond=cond)

    def gen_func_prolog(self):
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers])
        self.mc.SUB_ri(r.sp.value, r.sp.value,  WORD)
        self.mc.MOV_rr(r.fp.value, r.sp.value)

    def gen_bootstrap_code(self, inputargs, regalloc, looptoken):
        for i in range(len(inputargs)):
            loc = inputargs[i]
            reg = regalloc.force_allocate_reg(loc)
            if loc.type == REF:
                addr = self.fail_boxes_ptr.get_addr_for_num(i)
            elif loc.type == INT:
                addr = self.fail_boxes_int.get_addr_for_num(i)
            else:
                raise ValueError
            self.mc.gen_load_int(reg.value, addr)
            self.mc.LDR_ri(reg.value, reg.value)
            regalloc.possibly_free_var(loc)
        arglocs = [regalloc.loc(arg) for arg in inputargs]
        looptoken._arm_arglocs = arglocs
        return arglocs

    direct_bootstrap_code_size=100*WORD
    def gen_direct_bootstrap_code(self, arglocs, loop_head, regalloc):
        self.mc.ensure_can_fit(self.direct_bootstrap_code_size)
        self.gen_func_prolog()
        if len(arglocs) > 4:
            reg_args = 4
        else:
            reg_args = len(arglocs)

        stack_locs = len(arglocs) - reg_args

        for i in range(reg_args):
            loc = arglocs[i]
            self.mov_loc_loc(r.all_regs[i], loc)

        for i in range(stack_locs):
            loc = arglocs[reg_args + i]
            stack_position = (len(r.callee_saved_registers) + 1 +i)*WORD
            if loc.is_reg():
                self.mc.LDR_ri(loc.value, r.fp.value, stack_position)
            elif loc.is_stack():
                self.mc.LDR_ri(r.ip.value, r.fp.value, stack_position)
                self.mov_loc_loc(r.ip, loc)
            else:
                assert 0, 'invalid location'
        sp_patch_location = self._prepare_sp_patch_location()
        self.mc.B(loop_head)
        self._patch_sp_offset(sp_patch_location, regalloc)

    # cpu interface
    def assemble_loop(self, inputargs, operations, looptoken):
        self.setup()
        self.debug = False
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = ARMRegisterManager(longevity, assembler=self, frame_manager=ARMFrameManager())
        self.align()
        loop_start=self.mc.curraddr()
        self.gen_func_prolog()


        arglocs = self.gen_bootstrap_code(inputargs, regalloc, looptoken)
        sp_patch_location = self._prepare_sp_patch_location()

        loop_head=self.mc.curraddr()
        looptoken._arm_bootstrap_code = loop_start
        looptoken._arm_loop_code = loop_head
        print 'Loop', inputargs, operations
        self._walk_operations(operations, regalloc)

        self._patch_sp_offset(sp_patch_location, regalloc)

        self.align()

        looptoken._arm_direct_bootstrap_code = self.mc.curraddr()
        self.gen_direct_bootstrap_code(arglocs, loop_head, regalloc)

        if self._debug_asm:
            self._dump_trace('loop.asm')
        print 'Done assembling loop with token %r' % looptoken

    def _prepare_sp_patch_location(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update the
        sp according to the number of spilled variables"""
        size = (self.mc.size_of_gen_load_int+WORD)
        self.mc.ensure_can_fit(size)
        l = self.mc.curraddr()
        for _ in range(size//WORD):
            self.mc.MOV_rr(r.r0.value, r.r0.value)
        return l

    def _patch_sp_offset(self, addr, regalloc):
        cb = ARMv7InMemoryBuilder(addr, ARMv7InMemoryBuilder.size_of_gen_load_int)
        # Note: the frame_depth is one less than the value stored in the frame
        # manager
        if regalloc.frame_manager.frame_depth == 1:
            return
        n = (regalloc.frame_manager.frame_depth-1)*WORD
        self._adjust_sp(n, regalloc, cb, base_reg=r.fp)

    def _adjust_sp(self, n, regalloc, cb=None, fcond=c.AL, base_reg=r.sp):
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
            b = TempBox()
            reg = regalloc.force_allocate_reg(b)
            cb.gen_load_int(reg.value, n, cond=fcond)
            if rev:
                cb.ADD_rr(r.sp.value, base_reg.value, reg.value, cond=fcond)
            else:
                cb.SUB_rr(r.sp.value, base_reg.value, reg.value, cond=fcond)
            regalloc.possibly_free_var(b)

    def _walk_operations(self, operations, regalloc):
        fcond=c.AL
        i = 0
        while i < len(operations):
            op = operations[i]
            opnum = op.getopnum()
            if self.can_merge_with_next_guard(op, i, operations):
                fcond = self.operations_with_guard[opnum](self, op,
                                            operations[i+1], regalloc, fcond)
                i += 1
            else:
                fcond = self.operations[opnum](self, op, regalloc, fcond)
            i += 1

    def can_merge_with_next_guard(self, op, i, operations):
        if op.getopnum() == rop.CALL_MAY_FORCE or op.getopnum() == rop.CALL_ASSEMBLER:
            assert operations[i + 1].getopnum() == rop.GUARD_NOT_FORCED
            return True
        if op.getopnum() == rop.INT_MUL_OVF:
            opnum = operations[i + 1].getopnum()
            assert opnum  == rop.GUARD_OVERFLOW or opnum == rop.GUARD_NO_OVERFLOW
            return True
        return False

    def assemble_bridge(self, faildescr, inputargs, operations):
        self.setup()
        self.debug = False
        enc = rffi.cast(rffi.CCHARP, faildescr._failure_recovery_code)
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = ARMRegisterManager(longevity, assembler=self, frame_manager=ARMFrameManager())

        bridge_head = self.mc.curraddr()
        frame_depth = faildescr._arm_frame_depth
        locs = self.decode_inputargs(enc, inputargs, regalloc)
        regalloc.update_bindings(locs, frame_depth, inputargs)
        sp_patch_location = self._prepare_sp_patch_location()

        print 'Bridge', inputargs, operations
        self._walk_operations(operations, regalloc)

        self._patch_sp_offset(sp_patch_location, regalloc)

        print 'Done building bridges'
        self.patch_trace(faildescr, bridge_head, regalloc)
        print 'Done patching trace'
        if self._debug_asm:
            self._dump_trace('bridge.asm')


    def _dump_trace(self, name):
        self.mc._dump_trace(name)

    def _check_imm_arg(self, arg, size=0xFF, allow_zero=True):
        if isinstance(arg, ConstInt):
            if allow_zero:
                lower_bound = arg.getint() >= 0
            else:
                lower_bound = arg.getint() > 0
            return arg.getint() <= size and lower_bound
        return False

    def _ensure_value_is_boxed(self, thing, regalloc, forbidden_vars=[]):
        box = None
        loc = None
        if isinstance(thing, Const):
            if isinstance(thing, ConstInt):
                box = BoxInt()
            else:
                box = TempBox()
            loc = regalloc.force_allocate_reg(box,
                            forbidden_vars=forbidden_vars)
            imm = regalloc.convert_to_imm(thing)
            self.mc.gen_load_int(loc.value, imm.getint())
        else:
            loc = regalloc.make_sure_var_in_reg(thing,
                            forbidden_vars=forbidden_vars, imm_fine=False)
            box = thing
        return loc, box



    def _ensure_result_bit_extension(self, resloc, size, signed, regalloc):
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
                t = TempBox()
                loc = regalloc.force_allocate_reg(t)
                self.mc.gen_load_int(loc.value, 0xFFFF)
                self.mc.AND_rr(resloc.value, resloc.value, loc.value)
                regalloc.possibly_free_var(t)
            else:
                self.mc.LSL_ri(resloc.value, resloc.value, 16)
                self.mc.ASR_ri(resloc.value, resloc.value, 16)

    def patch_trace(self, faildescr, bridge_addr, regalloc):
        # The first instruction (word) is not overwritten, because it is the
        # one that actually checks the condition
        b = ARMv7InMemoryBuilder(faildescr._arm_guard_code,
                                        self.guard_size-WORD)
        b.B(bridge_addr, some_reg=r.lr)

    # regalloc support
    def regalloc_mov(self, prev_loc, loc):
        if prev_loc.is_imm():
            # XXX check size of imm for current instr
            self.mc.gen_load_int(loc.value, prev_loc.getint())
        elif loc.is_stack():
            self.mc.STR_ri(prev_loc.value, r.fp.value, loc.position*-WORD)
        elif prev_loc.is_stack():
            self.mc.LDR_ri(loc.value, r.fp.value, prev_loc.position*-WORD)
        else:
            self.mc.MOV_rr(loc.value, prev_loc.value)
    mov_loc_loc = regalloc_mov

    def regalloc_push(self, loc):
        if loc.is_stack():
            self.mc.LDR_ri(r.ip.value, r.fp.value, loc.position*-WORD)
            self.mc.PUSH([r.ip.value])
        elif loc.is_reg():
            self.mc.PUSH([loc.value])
        else:
            assert 0, 'ffuu'

    def regalloc_pop(self, loc):
        if loc.is_stack():
            self.mc.POP([r.ip.value])
            self.mc.STR_ri(r.ip.value, r.fp.value, loc.position*-WORD)
        elif loc.is_reg():
            self.mc.POP([loc.value])
        else:
            assert 0, 'ffuu'

    def leave_jitted_hook(self):
        pass

def make_operation_list():
    def notimplemented(self, op, regalloc, fcond):
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
    def notimplemented(self, op, guard_op, regalloc, fcond):
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
