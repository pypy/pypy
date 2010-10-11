from pypy.jit.backend.arm.codebuilder import ARMv7Builder
from pypy.jit.backend.arm import registers as r
from pypy.jit.backend.arm import conditions as c
from pypy.jit.backend.llsupport.regalloc import compute_vars_longevity
from pypy.jit.backend.arm.regalloc import ARMRegisterManager
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.history import ConstInt, Box
from pypy.rpython.lltypesystem import lltype
# XXX Move to llsupport
from pypy.jit.backend.x86.support import values_array


class AssemblerARM(object):

    def __init__(self, cpu, failargs_limit=1000):
        self.mc = ARMv7Builder()
        self.cpu = cpu
        self.input_arg_boxes_int = values_array(lltype.Signed, failargs_limit) # merge with fail_boxes_int later
        self.fail_boxes_int = values_array(lltype.Signed, failargs_limit)

    def assemble_loop(self, inputargs, operations, looptoken):
        assert len(inputargs) == 1
        longevity = compute_vars_longevity(inputargs, operations)
        regalloc = ARMRegisterManager(longevity, assembler=self.mc)
        self.gen_func_prolog()
        self.gen_bootstrap_code(inputargs, regalloc)
        loop_head=self.mc.curraddr()
        looptoken._arm_bootstrap_code = self.mc.baseaddr()
        looptoken._arm_loop_code = loop_head
        looptoken._temp_inputargs = inputargs#XXX remove
        fcond=c.AL
        for op in operations:
            opnum = op.getopnum()
            fcond = self.operations[opnum](self, op, regalloc, fcond)
        self.gen_func_epilog()
        f = open('loop.asm', 'wb')
        for i in range(self.mc._pos):
            f.write(self.mc._data[i])
        f.close()
        print 'Done assembling'

    def emit_op_jump(self, op, regalloc, fcond):
        tmp = Box()
        tmpreg = regalloc.try_allocate_reg(tmp)
        inputargs = op.getdescr()._temp_inputargs
        for i in range(op.numargs()):
            reg = regalloc.try_allocate_reg(op.getarg(i))
            inpreg = regalloc.try_allocate_reg(inputargs[i])
            # XXX only if every value is in a register
            self.mc.MOV_rr(inpreg, reg)
        loop_code = op.getdescr()._arm_loop_code
        self.gen_load_int(tmpreg, loop_code)
        self.mc.MOV_rr(r.pc, tmpreg)
        regalloc.possibly_free_var(tmpreg)
        return fcond

    def emit_op_finish(self, op, regalloc, fcond):
        self.gen_write_back(op, op.getarglist(), regalloc, fcond)
        return fcond

    def emit_op_int_le(self, op, regalloc, fcond):
        reg = regalloc.try_allocate_reg(op.getarg(0))
        assert isinstance(op.getarg(1), ConstInt)
        self.mc.CMP(reg, op.getarg(1).getint())
        return c.GT

    def emit_op_int_add(self, op, regalloc, fcond):
        reg = regalloc.try_allocate_reg(op.getarg(0))
        res = regalloc.try_allocate_reg(op.result)
        assert isinstance(op.getarg(1), ConstInt)
        self.mc.ADD_ri(res, reg, op.getarg(1).getint())
        regalloc.possibly_free_vars_for_op(op)
        return fcond

    def emit_op_guard_true(self, op, regalloc, fcond):
        assert fcond == c.GT
        self.gen_write_back(op, op.getfailargs(), regalloc, fcond)
        self.gen_func_epilog(cond=fcond)
        return c.AL

    def gen_write_back(self, op, args, regalloc, fcond):
        temp = Box()
        temp_reg = regalloc.try_allocate_reg(temp)
        for i in range(len(args)):
            reg = regalloc.try_allocate_reg(args[i])
            addr = self.fail_boxes_int.get_addr_for_num(i)
            self.gen_load_int(temp_reg, addr, cond=fcond)
            self.mc.STR_ri(reg, temp_reg, cond=fcond)

        regalloc.possibly_free_var(temp_reg)
        n = self.cpu.get_fail_descr_number(op.getdescr())
        self.mc.MOV_ri(r.r0, n, cond=fcond)

    def gen_func_epilog(self,cond=c.AL):
        self.mc.LDM(r.sp, r.callee_restored_registers, cond=cond)

    def gen_func_prolog(self):
        self.mc.PUSH(r.callee_saved_registers)

    def gen_bootstrap_code(self, inputargs, regalloc):
        for i in range(len(inputargs)):
            reg = regalloc.try_allocate_reg(inputargs[i])
            addr = self.input_arg_boxes_int.get_addr_for_num(i)
            self.gen_load_int(reg, addr)
            self.mc.LDR_ri(reg, reg)

    def gen_load_int(self, reg, value, cond=c.AL):
        assert reg != r.ip, 'ip is used to load int'
        self.mc.MOV_ri(reg, (value & 0xFF), cond=cond)

        for offset in range(8, 25, 8):
            self.mc.MOV_ri(r.ip, (value >> offset) & 0xFF, cond=cond)
            self.mc.ORR_rr(reg, reg, r.ip, offset, cond=cond)



def make_operation_list():
    def notimplemented(self, op, regalloc, fcond):
        raise NotImplementedError

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
