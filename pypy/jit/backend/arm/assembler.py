from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.arm import locations
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm.arch import WORD, FUNC_ALIGN
from pypy.jit.backend.arm.codebuilder import ARMv7Builder, ARMv7InMemoryBuilder
from pypy.jit.backend.arm.regalloc import ARMRegisterManager, ARMFrameManager
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity
from pypy.jit.metainterp.history import ConstInt, BoxInt, Box, BasicFailDescr
from pypy.jit.metainterp.resoperation import rop
from pypy.rlib import rgc
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.jit.backend.arm.opassembler import (GuardOpAssembler,
                                                IntOpAsslember,
                                                OpAssembler,
                                                UnaryIntOpAssembler)
# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array


class AssemblerARM(GuardOpAssembler, IntOpAsslember,
                    OpAssembler, UnaryIntOpAssembler):

    def __init__(self, cpu, failargs_limit=1000):
        self.mc = ARMv7Builder()
        self.cpu = cpu
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)
        self._debug_asm = True

        self._exit_code_addr = self.mc.curraddr()
        self._gen_exit_path()
        self.align()
        self.mc._start_addr = self.mc.curraddr()


    def setup_failure_recovery(self):

        @rgc.no_collect
        def failure_recovery_func(mem_loc, stackloc):
            """mem_loc is a structure in memory describing where the values for
            the failargs are stored. stacklock is the address of the stack
            section where the registers were saved."""
            enc = rffi.cast(rffi.CCHARP, mem_loc)
            stack = rffi.cast(rffi.CCHARP, stackloc)
            return self.decode_registers_and_descr(enc, stack)

        self.failure_recovery_func = failure_recovery_func

    @rgc.no_collect
    def decode_registers_and_descr(self, enc, stack):
        """Decode locations encoded in memory at enc and write the values to
        the failboxes.
        Registers are saved on the stack
        XXX Rest to follow"""
        i = -1
        fail_index = -1
        while(True):
            i += 1
            fail_index += 1
            res = enc[i]
            if res == '\xFE':
                continue
            if res == '\xFF':
                break
            if res == '\xFD':
                # imm value
                value = self.decode32(enc, i+1)
                i += 4
            elif res == '\xFC': # stack location
                stack_loc = self.decode32(enc, i+1)
                #XXX ffuu use propper calculation here
                value = self.decode32(stack, len(r.all_regs)*WORD+40-stack_loc*WORD)
                i += 4
            else: # an int for now
                reg = ord(enc[i])
                value = self.decode32(stack, reg*WORD)

            self.fail_boxes_int.setitem(fail_index, value)

        assert enc[i] == '\xFF'
        descr = self.decode32(enc, i+1)
        self.fail_boxes_count = fail_index
        return descr

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
        self.setup_failure_recovery()
        functype = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
        decode_registers_addr = llhelper(functype, self.failure_recovery_func)
        self.mc.PUSH([reg.value for reg in r.all_regs])     # registers r0 .. r10
        self.mc.MOV_rr(r.r0.value, r.lr.value)  # move mem block address, to r0 to pass as
                                    # parameter to next procedure call
        self.mc.MOV_rr(r.r1.value, r.sp.value)  # pass the current stack pointer as second param

        self.mc.BL(rffi.cast(lltype.Signed, decode_registers_addr))
        self.mc.MOV_rr(r.ip.value, r.r0.value)
        self.mc.LDM(r.sp.value, [reg.value for reg in r.all_regs], w=1) # XXX Replace with POP instr. someday
        self.mc.MOV_rr(r.r0.value, r.ip.value)
        self.gen_func_epilog()

    def _gen_path_to_exit_path(self, op, args, regalloc, fcond=c.AL):
        """
        \xFC = stack location
        \xFD = imm location
        \xFE = Empty arg
        """

        box = Box()
        reg = regalloc.force_allocate_reg(box)
        # XXX free this memory
        mem = lltype.malloc(rffi.CArray(lltype.Char), (len(args)+5)*4, flavor='raw')
        i = 0
        j = 0
        while(i < len(args)):
            if args[i]:
                loc = regalloc.loc(args[i])
                if loc.is_reg():
                    mem[j] = chr(loc.value)
                    j += 1
                elif loc.is_imm():
                    mem[j] = '\xFD'
                    self.encode32(mem, j+1, loc.getint())
                    j += 5
                else:
                    #print 'Encoding a stack location'
                    mem[j] = '\xFC'
                    self.encode32(mem, j+1, loc.position)
                    j += 5
            else:
                mem[j] = '\xFE'
                j += 1
            i += 1

        mem[j] = chr(0xFF)
        memaddr = rffi.cast(lltype.Signed, mem)


        n = self.cpu.get_fail_descr_number(op.getdescr())
        self.encode32(mem, j+1, n)
        self.mc.gen_load_int(r.lr.value, memaddr, cond=fcond) # use lr to pass an argument
        self.mc.B(self._exit_code_addr, fcond, reg)

        # This register is used for patching when assembling a bridge
        # guards going to be patched are allways conditional
        if fcond != c.AL:
            op.getdescr()._arm_guard_reg = reg
        else:
            regalloc.possibly_free_var(reg)
        return memaddr

    def align(self):
        while(self.mc.curraddr() % FUNC_ALIGN != 0):
            self.mc.writechar(chr(0))

    epilog_size = 2*WORD
    def gen_func_epilog(self,cond=c.AL):
        self.mc.MOV_rr(r.sp.value, r.fp.value)
        self.mc.LDM(r.sp.value, [reg.value for reg in r.callee_restored_registers], cond=cond, w=1)

    def gen_func_prolog(self):
        self.mc.PUSH([reg.value for reg in r.callee_saved_registers])
        self.mc.MOV_rr(r.fp.value, r.sp.value)

    def gen_bootstrap_code(self, inputargs, regalloc, looptoken):
        regs = []
        for i in range(len(inputargs)):
            reg = regalloc.force_allocate_reg(inputargs[i])
            addr = self.fail_boxes_int.get_addr_for_num(i)
            self.mc.gen_load_int(reg.value, addr)
            self.mc.LDR_ri(reg.value, reg.value)
            regs.append(reg)
        looptoken._arm_arglocs = regs

    # cpu interface
    def assemble_loop(self, inputargs, operations, looptoken):
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = ARMRegisterManager(longevity, assembler=self, frame_manager=ARMFrameManager())
        self.align()
        loop_start=self.mc.curraddr()
        self.gen_func_prolog()

        sp_patch_location = self._prepare_sp_patch_location()

        self.gen_bootstrap_code(inputargs, regalloc, looptoken)
        loop_head=self.mc.curraddr()
        looptoken._arm_bootstrap_code = loop_start
        looptoken._arm_loop_code = loop_head
        fcond=c.AL
        print inputargs, operations
        for op in operations:
            # XXX consider merging ops with next one if it is an adecuate guard
            opnum = op.getopnum()
            fcond = self.operations[opnum](self, op, regalloc, fcond)

        self._patch_sp_offset(sp_patch_location, regalloc)

        if self._debug_asm:
            self._dump_trace('loop.asm')
        print 'Done assembling'

    def _prepare_sp_patch_location(self):
        """Generate NOPs as placeholder to patch the instruction(s) to update the
        sp according to the number of spilled variables"""
        l = self.mc.curraddr()
        for _ in range((self.mc.size_of_gen_load_int+WORD)//WORD):
            self.mc.MOV_rr(r.r0.value, r.r0.value)
        return l

    def _patch_sp_offset(self, addr, regalloc):
        cb = ARMv7InMemoryBuilder(addr, ARMv7InMemoryBuilder.size_of_gen_load_int)
        if regalloc.frame_manager.frame_depth == 1:
            return
        n = regalloc.frame_manager.frame_depth*WORD
        self._adjust_sp(n, cb)

    def _adjust_sp(self, n, cb=None, fcond=c.AL):
        if cb is None:
            cb = self.mc
        if n <= 0xFF and fcond == c.AL:
            cb.SUB_ri(r.sp.value, r.sp.value, n)
        else:
            b = Box()
            reg = regalloc.force_allocate_reg(b)
            cb.gen_load_int(reg.value, n, cond=fcond)
            cb.SUB_rr(r.sp.value, r.sp.value, reg.value, cond=fcond)
            regalloc.possibly_free_var(reg)

    def assemble_bridge(self, faildescr, inputargs, operations):
        enc = rffi.cast(rffi.CCHARP, faildescr._failure_recovery_code)
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = ARMRegisterManager(longevity, assembler=self, frame_manager=ARMFrameManager())

        regalloc.update_bindings(enc, inputargs)
        bridge_head = self.mc.curraddr()

        fcond = c.AL
        for op in operations:
            opnum = op.getopnum()
            fcond = self.operations[opnum](self, op, regalloc, fcond)
        self.gen_func_epilog()
        print 'Done building bridges'
        self.patch_trace(faildescr, bridge_head)
        print 'Done patching trace'
        if self._debug_asm:
            self._dump_trace('bridge.asm')


    def _dump_trace(self, name):
        self.mc._dump_trace(name)

    def _check_imm_arg(self, arg, size=0xFF, allow_zero=True):
        if allow_zero:
            lower_bound = arg.getint() >= 0
        else:
            lower_bound = arg.getint() > 0
        #XXX check ranges for different operations
        return isinstance(arg, ConstInt) and arg.getint() <= size and lower_bound

    def patch_trace(self, faildescr, bridge_addr):
        # XXX make sure there is enough space at patch target
        fcond = faildescr._arm_guard_cond
        b = ARMv7InMemoryBuilder(faildescr._arm_guard_code, faildescr._arm_guard_size)
        b.B(bridge_addr, fcond, some_reg=faildescr._arm_guard_reg)

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

AssemblerARM.operations = make_operation_list()
