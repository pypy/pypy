import py
from rpython.jit.metainterp.compile import ResumeGuardDescr
from rpython.jit.metainterp.history import (ConstInt, INT, REF,
    FLOAT, VECTOR, TargetToken)
from rpython.jit.backend.llsupport.descr import (ArrayDescr, CallDescr,
    unpack_arraydescr, unpack_fielddescr, unpack_interiorfielddescr)
from rpython.jit.backend.llsupport.regalloc import get_scale
from rpython.jit.metainterp.resoperation import (rop, ResOperation,
        VectorOp, VectorGuardOp)
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem import lltype
from rpython.jit.backend.ppc.locations import imm, RegisterLocation
from rpython.jit.backend.ppc.arch import IS_BIG_ENDIAN
from rpython.jit.backend.llsupport.vector_ext import VectorExt
from rpython.jit.backend.ppc.arch import PARAM_SAVE_AREA_OFFSET
import rpython.jit.backend.ppc.register as r
import rpython.jit.backend.ppc.condition as c
import rpython.jit.backend.ppc.locations as l
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.codewriter import longlong

def not_implemented(msg):
    msg = '[ppc/vector_ext] %s\n' % msg
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)

def flush_vec_cc(asm, regalloc, condition, size, result_loc):
    # After emitting an instruction that leaves a boolean result in
    # a condition code (cc), call this.  In the common case, result_loc
    # will be set to SPP by the regalloc, which in this case means
    # "propagate it between this operation and the next guard by keeping
    # it in the cc".  In the uncommon case, result_loc is another
    # register, and we emit a load from the cc into this register.
    assert asm.guard_success_cc == c.cond_none
    if result_loc is r.SPP:
        asm.guard_success_cc = condition
    else:
        resval = result_loc.value
        # either doubleword integer 1 (2x) or word integer 1 (4x)
        ones = regalloc.ivrm.get_scratch_reg().value
        zeros = regalloc.ivrm.get_scratch_reg().value
        asm.mc.vxor(zeros, zeros, zeros)
        if size == 4:
            asm.mc.vspltisw(ones, 1)
        else:
            assert size == 8
            tloc = regalloc.rm.get_scratch_reg()
            asm.mc.load_imm(tloc, asm.VEC_DOUBLE_WORD_ONES)
            asm.mc.lvx(ones, 0, tloc.value)
        asm.mc.vsel(resval, zeros, ones, resval)

class AltiVectorExt(VectorExt):
    pass

class VectorAssembler(object):
    _mixin_ = True

    VEC_DOUBLE_WORD_ONES = 0

    def setup_once_vector(self):
        if IS_BIG_ENDIAN:
            # 2x 64 bit signed integer(1) BE
            data = (b'\x00' * 7 + b'\x01') * 2
        else:
            # 2x 64 bit signed integer(1) LE
            data = (b'\x01' + b'\x00' * 7) * 2
        datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr, [])
        mem = datablockwrapper.malloc_aligned(len(data), alignment=16)
        datablockwrapper.done()
        addr = rffi.cast(rffi.CArrayPtr(lltype.Char), mem)
        for i in range(len(data)):
            addr[i] = data[i]
        self.VEC_DOUBLE_WORD_ONES = mem

    def emit_vec_load_f(self, op, arglocs, regalloc):
        resloc, baseloc, indexloc, size_loc, ofs, integer_loc, aligned_loc = arglocs
        #src_addr = addr_add(baseloc, ofs_loc, ofs.value, 0)
        assert ofs.value == 0
        itemsize = size_loc.value
        if itemsize == 4:
            self.mc.lxvw4x(resloc.value, indexloc.value, baseloc.value)
        elif itemsize == 8:
            self.mc.lxvd2x(resloc.value, indexloc.value, baseloc.value)

    def emit_vec_load_i(self, op, arglocs, regalloc):
        resloc, baseloc, indexloc, size_loc, ofs, \
            Vhiloc, Vloloc, Vploc, tloc = arglocs
        #src_addr = addr_add(base_loc, ofs_loc, ofs.value, 0)
        assert ofs.value == 0
        Vlo = Vloloc.value
        Vhi = Vhiloc.value
        self.mc.lvx(Vhi, indexloc.value, baseloc.value)
        Vp = Vploc.value
        t = tloc.value
        if IS_BIG_ENDIAN:
            self.mc.lvsl(Vp, indexloc.value, baseloc.value)
        else:
            self.mc.lvsr(Vp, indexloc.value, baseloc.value)
        self.mc.addi(t, baseloc.value, 16)
        self.mc.lvx(Vlo, indexloc.value, t)
        if IS_BIG_ENDIAN:
            self.mc.vperm(resloc.value, Vhi, Vlo, Vp)
        else:
            self.mc.vperm(resloc.value, Vlo, Vhi, Vp)

    def _emit_vec_setitem(self, op, arglocs, regalloc):
        # prepares item scale (raw_store does not)
        base_loc, ofs_loc, value_loc, size_loc, baseofs, integer_loc, aligned_loc = arglocs
        scale = get_scale(size_loc.value)
        dest_loc = addr_add(base_loc, ofs_loc, baseofs.value, scale)
        self._vec_store(dest_loc, value_loc, integer_loc.value,
                        size_loc.value, aligned_loc.value)

    genop_discard_vec_setarrayitem_raw = _emit_vec_setitem
    genop_discard_vec_setarrayitem_gc = _emit_vec_setitem

    def emit_vec_store(self, op, arglocs, regalloc):
        baseloc, indexloc, valueloc, sizeloc, baseofs, \
            integer_loc, aligned_loc = arglocs
        #dest_loc = addr_add(base_loc, ofs_loc, baseofs.value, 0)
        assert baseofs.value == 0
        if integer_loc.value:
            Vloloc = regalloc.ivrm.get_scratch_reg()
            Vhiloc = regalloc.ivrm.get_scratch_reg()
            Vploc = regalloc.ivrm.get_scratch_reg()
            tloc = regalloc.rm.get_scratch_reg()
            V1sloc = regalloc.ivrm.get_scratch_reg()
            V1s = V1sloc.value
            V0sloc = regalloc.ivrm.get_scratch_reg()
            V0s = V0sloc.value
            Vmaskloc = regalloc.ivrm.get_scratch_reg()
            Vmask = Vmaskloc.value
            Vlo = Vhiloc.value
            Vhi = Vloloc.value
            Vp = Vploc.value
            t = tloc.value
            Vs = valueloc.value
            # UFF, that is a lot of code for storing unaligned!
            # probably a lot of room for improvement (not locally,
            # but in general for the algorithm)
            self.mc.lvx(Vhi, indexloc.value, baseloc.value)
            #self.mc.lvsr(Vp, indexloc.value, baseloc.value)
            if IS_BIG_ENDIAN:
                self.mc.lvsr(Vp, indexloc.value, baseloc.value)
            else:
                self.mc.lvsl(Vp, indexloc.value, baseloc.value)
            self.mc.addi(t, baseloc.value, 16)
            self.mc.lvx(Vlo, indexloc.value, t)
            self.mc.vspltisb(V1s, -1)
            self.mc.vspltisb(V0s, 0)
            if IS_BIG_ENDIAN:
                self.mc.vperm(Vmask, V0s, V1s, Vp)
            else:
                self.mc.vperm(Vmask, V1s, V0s, Vp)
            self.mc.vperm(Vs, Vs, Vs, Vp)
            self.mc.vsel(Vlo, Vs, Vlo, Vmask)
            self.mc.vsel(Vhi, Vhi, Vs, Vmask)
            self.mc.stvx(Vlo, indexloc.value, t)
            self.mc.stvx(Vhi, indexloc.value, baseloc.value)
        else:
            itemsize = sizeloc.value
            if itemsize == 4:
                self.mc.stxvw4x(valueloc.value, indexloc.value, baseloc.value)
            elif itemsize == 8:
                self.mc.stxvd2x(valueloc.value, indexloc.value, baseloc.value)

    def emit_vec_int_add(self, op, arglocs, regalloc):
        resloc, loc0, loc1, size_loc = arglocs
        size = size_loc.value
        if size == 1:
            self.mc.vaddubm(resloc.value, loc0.value, loc1.value)
        elif size == 2:
            self.mc.vadduhm(resloc.value, loc0.value, loc1.value)
        elif size == 4:
            self.mc.vadduwm(resloc.value, loc0.value, loc1.value)
        elif size == 8:
            self.mc.vaddudm(resloc.value, loc0.value, loc1.value)

    def emit_vec_int_sub(self, op, arglocs, regalloc):
        resloc, loc0, loc1, size_loc = arglocs
        size = size_loc.value
        if size == 1:
            # TODO verify if unsigned subtract is the wanted feature
            self.mc.vsububm(resloc.value, loc0.value, loc1.value)
        elif size == 2:
            # TODO verify if unsigned subtract is the wanted feature
            self.mc.vsubuhm(resloc.value, loc0.value, loc1.value)
        elif size == 4:
            # TODO verify if unsigned subtract is the wanted feature
            self.mc.vsubuwm(resloc.value, loc0.value, loc1.value)
        elif size == 8:
            self.mc.vsubudm(resloc.value, loc0.value, loc1.value)

    def emit_vec_float_add(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 4:
            self.mc.xvaddsp(resloc.value, loc0.value, loc1.value)
        elif itemsize == 8:
            self.mc.xvadddp(resloc.value, loc0.value, loc1.value)

    def emit_vec_float_sub(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 4:
            self.mc.xvsubsp(resloc.value, loc0.value, loc1.value)
        elif itemsize == 8:
            self.mc.xvsubdp(resloc.value, loc0.value, loc1.value)

    def emit_vec_float_mul(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 4:
            self.mc.xvmulsp(resloc.value, loc0.value, loc1.value)
        elif itemsize == 8:
            self.mc.xvmuldp(resloc.value, loc0.value, loc1.value)

    def emit_vec_float_truediv(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 4:
            self.mc.xvdivsp(resloc.value, loc0.value, loc1.value)
        elif itemsize == 8:
            self.mc.xvdivdp(resloc.value, loc0.value, loc1.value)

    def emit_vec_int_mul(self, op, arglocs, regalloc):
        raise NotImplementedError
        pass # TODO

    def emit_vec_int_and(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.vand(resloc.value, loc0.value, loc1.value)

    def emit_vec_int_or(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.vor(resloc.value, loc0.value, loc1.value)

    def emit_vec_int_xor(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.veqv(resloc.value, loc0.value, loc1.value)

    def emit_vec_int_signext(self, op, arglocs, regalloc):
        resloc, loc0 = arglocs
        # TODO
        self.regalloc_mov(loc0, resloc)

    def emit_vec_float_abs(self, op, arglocs, regalloc):
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        if size == 4:
            self.mc.xvabssp(resloc.value, argloc.value)
        elif size == 8:
            self.mc.xvabsdp(resloc.value, argloc.value)
        else:
            notimplemented("[ppc/assembler] float abs for size %d" % size)

    def emit_vec_float_neg(self, op, arglocs, regalloc):
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        if size == 4:
            self.mc.xvnegsp(resloc.value, argloc.value)
        elif size == 8:
            self.mc.xvnegdp(resloc.value, argloc.value)
        else:
            notimplemented("[ppc/assembler] float neg for size %d" % size)

    def emit_vec_guard_true(self, guard_op, arglocs, regalloc):
        self._emit_guard(guard_op, arglocs)

    def emit_vec_guard_false(self, guard_op, arglocs, regalloc):
        self.guard_success_cc = c.negate(self.guard_success_cc)
        self._emit_guard(guard_op, arglocs)

    #def guard_vector(self, guard_op, regalloc, true):
    #    assert isinstance(guard_op, VectorGuardOp)
    #    arg = guard_op.getarg(0)
    #    assert isinstance(arg, VectorOp)
    #    size = arg.bytesize
    #    temp = regalloc.get_scratch_reg().value
    #    load = arg.bytesize * arg.count - self.cpu.vector_register_size
    #    assert load == 0
    #    if true:
    #        pass
    #        #self.mc.PXOR(temp, temp)
    #        # if the vector is not fully packed blend 1s
    #        #if load < 0:
    #        #    self.mc.PCMPEQQ(temp, temp) # fill with ones
    #        #    self._blend_unused_slots(loc, arg, temp)
    #        #    # reset to zeros
    #        #    self.mc.PXOR(temp, temp)

    #        # cmp with zeros (in temp) creates ones at each slot where it is zero
    #        #self.mc.PCMPEQ(loc, temp, size)
    #        ## temp converted to ones
    #        #self.mc.PCMPEQQ(temp, temp)
    #        ## test if all slots are zero
    #        #self.mc.PTEST(loc, temp)
    #        #self.guard_success_cc = rx86.Conditions['Z']
    #    else:
    #        # if the vector is not fully packed blend 1s
    #        #if load < 0:
    #        #    temp = X86_64_XMM_SCRATCH_REG
    #        #    self.mc.PXOR(temp, temp)
    #        #    self._blend_unused_slots(loc, arg, temp)
    #        #self.mc.PTEST(loc, loc)
    #        self.guard_success_cc = rx86.Conditions['NZ']

    #def _blend_unused_slots(self, loc, arg, temp):
    #    select = 0
    #    bits_used = (arg.count * arg.bytesize * 8)
    #    index = bits_used // 16
    #    while index < 8:
    #        select |= (1 << index)
    #        index += 1
    #    self.mc.PBLENDW_xxi(loc.value, temp.value, select)

    def _update_at_exit(self, fail_locs, fail_args, faildescr, regalloc):
        """ If accumulation is done in this loop, at the guard exit
            some vector registers must be adjusted to yield the correct value
        """
        if not isinstance(faildescr, ResumeGuardDescr):
            return
        accum_info = faildescr.rd_vector_info
        while accum_info:
            pos = accum_info.getpos_in_failargs()
            scalar_loc = fail_locs[pos]
            vector_loc = accum_info.location
            # the upper elements will be lost if saved to the stack!
            scalar_arg = accum_info.getoriginal()
            if not scalar_loc.is_reg():
                scalar_loc = regalloc.force_allocate_reg(scalar_arg)
            assert scalar_arg is not None
            op = accum_info.accum_operation
            self._accum_reduce(op, scalar_arg, vector_loc, scalar_loc)
            accum_info = accum_info.next()

    def _accum_reduce(self, op, arg, accumloc, targetloc):
        # Currently the accumulator can ONLY be the biggest
        # 64 bit float/int
        tgt = targetloc.value
        acc = accumloc.value
        if arg.type == FLOAT:
            # r = (r[0]+r[1],r[0]+r[1])
            if IS_BIG_ENDIAN:
                self.mc.xxspltd(tgt, acc, acc, 0b00)
            else:
                self.mc.xxspltd(tgt, acc, acc, 0b10)
            if op == '+':
                self.mc.xsadddp(tgt, tgt, acc)
            elif op == '*':
                self.mc.xsmuldp(tgt, tgt, acc)
            else:
                not_implemented("sum not implemented")
            return
        else:
            assert arg.type == INT
            self.mc.load_imm(r.SCRATCH2, PARAM_SAVE_AREA_OFFSET)
            self.mc.stvx(acc, r.SCRATCH2.value, r.SP.value)
            self.mc.load(tgt, r.SP.value, PARAM_SAVE_AREA_OFFSET)
            self.mc.load(r.SCRATCH.value, r.SP.value, PARAM_SAVE_AREA_OFFSET+8)
            if op == '+':
                self.mc.add(tgt, tgt, acc)
            elif op == '*':
                self.mc.mul(tgt, tgt, acc)
            else:
                not_implemented("sum not implemented")
            return

        not_implemented("reduce sum for %s not impl." % arg)

    def emit_vec_int_is_true(self, op, arglocs, regalloc):
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.ivrm.get_scratch_reg().value
        self.mc.vxor(tmp, tmp, tmp)
        # argloc[i] > 0:
        # For an unsigned integer that is equivalent to argloc[i] != 0
        if size == 1:
            self.mc.vcmpgtubx(resloc.value, argloc.value, tmp)
        elif size == 2:
            self.mc.vcmpgtuhx(resloc.value, argloc.value, tmp)
        elif size == 4:
            self.mc.vcmpgtuwx(resloc.value, argloc.value, tmp)
        elif size == 8:
            self.mc.vcmpgtudx(resloc.value, argloc.value, tmp)

    def emit_vec_float_eq(self, op, arglocs, regalloc):
        resloc, loc1, loc2, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.vrm.get_scratch_reg().value
        offloc = regalloc.rm.get_scratch_reg()
        off = offloc.value
        # SP is always 16 byte aligned, and PARAM_SAVE_AREA_OFFSET % 16 == 0
        self.mc.load_imm(offloc, PARAM_SAVE_AREA_OFFSET)
        if size == 4:
            self.mc.xvcmpeqspx(tmp, loc1.value, loc2.value)
            self.mc.stxvw4x(tmp, off, r.SP.value)
        elif size == 8:
            self.mc.xvcmpeqdpx(tmp, loc1.value, loc2.value)
            self.mc.stxvd2x(tmp, off, r.SP.value)
        else:
            notimplemented("[ppc/assembler] float == for size %d" % size)
        self.mc.lvx(resloc.value, off, r.SP.value)
        flush_vec_cc(self, regalloc, c.EQ, op.bytesize, resloc)

    def emit_vec_float_xor(self, op, arglocs, regalloc):
        resloc, l0, l1, sizeloc = arglocs
        res = resloc.value
        r0 = l0.value
        r1 = l1.value
        self.mc.xxlxor(res, r0, r1)

    def emit_vec_float_ne(self, op, arglocs, regalloc):
        resloc, loc1, loc2, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.vrm.get_scratch_reg().value
        offloc = regalloc.rm.get_scratch_reg()
        off = offloc.value
        # SP is always 16 byte aligned, and PARAM_SAVE_AREA_OFFSET % 16 == 0
        self.mc.load_imm(offloc, PARAM_SAVE_AREA_OFFSET)
        if size == 4:
            self.mc.xvcmpeqspx(tmp, loc1.value, loc2.value)
            self.mc.stxvw4x(tmp, off, r.SP.value)
        elif size == 8:
            self.mc.xvcmpeqdpx(tmp, loc1.value, loc2.value)
            self.mc.stxvd2x(tmp, off, r.SP.value)
        else:
            notimplemented("[ppc/assembler] float == for size %d" % size)
        res = resloc.value
        self.mc.lvx(res, off, r.SP.value)
        self.mc.vnor(res, res, res) # complement
        flush_vec_cc(self, regalloc, c.NE, op.bytesize, resloc)

    def emit_vec_cast_int_to_float(self, op, arglocs, regalloc):
        res, l0 = arglocs
        offloc = regalloc.rm.get_scratch_reg()
        off = offloc.value
        # SP is always 16 byte aligned, and PARAM_SAVE_AREA_OFFSET % 16 == 0
        self.mc.load_imm(offloc, PARAM_SAVE_AREA_OFFSET)
        self.mc.stvx(l0.value, off, r.SP.value)
        self.mc.lxvd2x(res.value, off, r.SP.value)
        self.mc.xvcvsxddp(res.value, res.value)

    def emit_vec_int_eq(self, op, arglocs, regalloc):
        res, l0, l1, sizeloc = arglocs
        size = sizeloc.value
        if size == 1:
            self.mc.vcmpequbx(res.value, l0.value, l1.value)
        elif size == 2:
            self.mc.vcmpequhx(res.value, l0.value, l1.value)
        elif size == 4:
            self.mc.vcmpequwx(res.value, l0.value, l1.value)
        elif size == 8:
            self.mc.vcmpequdx(res.value, l0.value, l1.value)
        flush_vec_cc(self, regalloc, c.EQ, op.bytesize, res)

    def emit_vec_int_ne(self, op, arglocs, regalloc):
        res, l0, l1, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.get_scratch_reg().value
        self.mc.vxor(tmp, tmp, tmp)
        if size == 1:
            self.mc.vcmpequbx(res.value, res.value, tmp)
        elif size == 2:
            self.mc.vcmpequhx(res.value, res.value, tmp)
        elif size == 4:
            self.mc.vcmpequwx(res.value, res.value, tmp)
        elif size == 8:
            self.mc.vcmpequdx(res.value, res.value, tmp)
        self.mc.vnor(res.value, res.value, res.value)
        flush_vec_cc(self, regalloc, c.NE, op.bytesize, res)

    def emit_vec_expand_f(self, op, arglocs, regalloc):
        resloc, srcloc = arglocs
        size = op.bytesize
        res = resloc.value
        if isinstance(srcloc, l.ConstFloatLoc):
            # they are aligned!
            assert size == 8
            tloc = regalloc.rm.get_scratch_reg()
            self.mc.load_imm(tloc, srcloc.value)
            self.mc.lxvd2x(res, 0, tloc.value)
        elif size == 8:
            # splat the low of src to both slots in res
            src = srcloc.value
            self.mc.xxspltdl(res, src, src)
        else:
            notimplemented("[ppc/assembler] vec expand in this combination not supported")

    def emit_vec_expand_i(self, op, arglocs, regalloc):
        res, l0, off = arglocs
        size = op.bytesize

        self.mc.load_imm(r.SCRATCH2, off.value)
        self.mc.lvx(res.value, r.SCRATCH2.value, r.SP.value)
        if size == 1:
            if IS_BIG_ENDIAN:
                self.mc.vspltb(res.value, res.value, 0b0000)
            else:
                self.mc.vspltb(res.value, res.value, 0b1111)
        elif size == 2:
            if IS_BIG_ENDIAN:
                self.mc.vsplth(res.value, res.value, 0b000)
            else:
                self.mc.vsplth(res.value, res.value, 0b111)
        elif size == 4:
            if IS_BIG_ENDIAN:
                self.mc.vspltw(res.value, res.value, 0b00)
            else:
                self.mc.vspltw(res.value, res.value, 0b11)
        elif size == 8:
            pass
        else:
            notimplemented("[expand int size not impl]")

    def emit_vec_pack_i(self, op, arglocs, regalloc):
        resultloc, vloc, sourceloc, residxloc, srcidxloc, countloc = arglocs
        srcidx = srcidxloc.value
        residx = residxloc.value
        count = countloc.value
        res = resultloc.value
        vector = vloc.value
        src = sourceloc.value
        size = op.bytesize
        if size == 8:
            if resultloc.is_vector_reg(): # vector <- reg
                self.mc.load_imm(r.SCRATCH, PARAM_SAVE_AREA_OFFSET)
                self.mc.stvx(vector, r.SCRATCH2.value, r.SP.value)
                self.mc.store(src, r.SP.value, PARAM_SAVE_AREA_OFFSET+8*residx)
                self.mc.lvx(res, r.SCRATCH2.value, r.SP.value)
            else:
                notimplemented("[ppc/vec_pack_i] 64 bit float")
        elif size == 4:
            notimplemented("[ppc/vec_pack_i]")
        elif size == 2:
            notimplemented("[ppc/vec_pack_i]")
        elif size == 1:
            notimplemented("[ppc/vec_pack_i]")

    def emit_vec_unpack_i(self, op, arglocs, regalloc):
        resloc, srcloc, idxloc, countloc = arglocs
        idx = idxloc.value
        res = resloc.value
        src = srcloc.value
        size = op.bytesize
        if size == 8:
            if srcloc.is_vector_reg(): # reg <- vector
                assert not resloc.is_vector_reg()
                self.mc.load_imm(r.SCRATCH, PARAM_SAVE_AREA_OFFSET)
                self.mc.stvx(src, r.SCRATCH2.value, r.SP.value)
                self.mc.load(res, r.SP.value, PARAM_SAVE_AREA_OFFSET+8*idx)
            else:
                notimplemented("[ppc/vec_unpack_i] 64 bit integer")

    def emit_vec_pack_f(self, op, arglocs, regalloc):
        resloc, vloc, srcloc, residxloc, srcidxloc, countloc = arglocs
        vec = vloc.value
        res = resloc.value
        src = srcloc.value
        count = countloc.value
        residx = residxloc.value
        srcidx = srcidxloc.value
        size = op.bytesize
        assert size == 8
        # srcloc is always a floating point register f, this means it is
        # vsr[0] == valueof(f)
        if srcidx == 0:
            if residx == 0:
                # r = (s[0], r[1])
                if IS_BIG_ENDIAN:
                    self.mc.xxspltd(res, src, vec, 0b10)
                else:
                    self.mc.xxspltd(res, src, vec, 0b01)
            else:
                assert residx == 1
                # r = (r[0], s[0])
                if IS_BIG_ENDIAN:
                    self.mc.xxspltd(res, vec, src, 0b00)
                else:
                    self.mc.xxspltd(res, vec, src, 0b11)
        else:
            assert srcidx == 1
            if residx == 0:
                # r = (s[1], r[1])
                if IS_BIG_ENDIAN:
                    self.mc.xxspltd(res, src, vec, 0b11)
                else:
                    self.mc.xxspltd(res, src, vec, 0b00)
            else:
                assert residx == 1
                # r = (r[0], s[1])
                if IS_BIG_ENDIAN:
                    self.mc.xxspltd(res, vec, src, 0b10)
                else:
                    self.mc.xxspltd(res, vec, src, 0b01)

    def emit_vec_unpack_f(self, op, arglocs, regalloc):
        resloc, srcloc, idxloc, countloc = arglocs
        self.emit_vec_pack_f(op, [resloc, srcloc, srcloc, imm(0), idxloc, countloc], regalloc)

    # needed as soon as PPC's support_singlefloat is implemented!
    #def genop_vec_cast_float_to_int(self, op, arglocs, regalloc):
    #    self.mc.CVTPD2DQ(resloc, arglocs[0])
    #def genop_vec_cast_singlefloat_to_float(self, op, arglocs, regalloc):
    #    self.mc.CVTPS2PD(resloc, arglocs[0])

    def emit_vec_f(self, op, arglocs, regalloc):
        pass
    emit_vec_i = emit_vec_f

class VectorRegalloc(object):
    _mixin_ = True

    def force_allocate_vector_reg(self, op):
        forbidden_vars = self.vrm.temp_boxes
        if op.type == FLOAT:
            return self.vrm.force_allocate_reg(op, forbidden_vars)
        else:
            return self.ivrm.force_allocate_reg(op, forbidden_vars)

    def ensure_vector_reg(self, box):
        if box.type == FLOAT:
            return self.vrm.make_sure_var_in_reg(box,
                               forbidden_vars=self.vrm.temp_boxes)
        else:
            return self.ivrm.make_sure_var_in_reg(box,
                               forbidden_vars=self.ivrm.temp_boxes)

    def _prepare_load(self, op):
        descr = op.getdescr()
        assert isinstance(descr, ArrayDescr)
        assert not descr.is_array_of_pointers() and \
               not descr.is_array_of_structs()
        itemsize, ofs, _ = unpack_arraydescr(descr)
        integer = not (descr.is_array_of_floats() or descr.getconcrete_type() == FLOAT)
        aligned = False
        args = op.getarglist()
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        base_loc = self.ensure_reg(a0)
        ofs_loc = self.ensure_reg(a1)
        result_loc = self.force_allocate_vector_reg(op)
        return [result_loc, base_loc, ofs_loc, imm(itemsize), imm(ofs),
                imm(integer), imm(aligned)]

    def _prepare_load_i(self, op):
        descr = op.getdescr()
        assert isinstance(descr, ArrayDescr)
        assert not descr.is_array_of_pointers() and \
               not descr.is_array_of_structs()
        itemsize, ofs, _ = unpack_arraydescr(descr)
        args = op.getarglist()
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        base_loc = self.ensure_reg(a0)
        ofs_loc = self.ensure_reg(a1)
        result_loc = self.force_allocate_vector_reg(op)
        tloc = self.rm.get_scratch_reg()
        Vhiloc = self.ivrm.get_scratch_reg()
        Vloloc = self.ivrm.get_scratch_reg()
        Vploc = self.ivrm.get_scratch_reg()
        return [result_loc, base_loc, ofs_loc, imm(itemsize), imm(ofs),
                Vhiloc, Vloloc, Vploc, tloc]

    prepare_vec_load_i = _prepare_load_i
    prepare_vec_load_f = _prepare_load

    def prepare_vec_arith(self, op):
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        assert isinstance(op, VectorOp)
        size = op.bytesize
        args = op.getarglist()
        loc0 = self.ensure_vector_reg(a0)
        loc1 = self.ensure_vector_reg(a1)
        resloc = self.force_allocate_vector_reg(op)
        return [resloc, loc0, loc1, imm(size)]

    prepare_vec_int_add = prepare_vec_arith
    prepare_vec_int_sub = prepare_vec_arith
    prepare_vec_int_mul = prepare_vec_arith
    prepare_vec_float_add = prepare_vec_arith
    prepare_vec_float_sub = prepare_vec_arith
    prepare_vec_float_mul = prepare_vec_arith
    prepare_vec_float_truediv = prepare_vec_arith

    # logic functions
    prepare_vec_int_and = prepare_vec_arith
    prepare_vec_int_or = prepare_vec_arith
    prepare_vec_int_xor = prepare_vec_arith

    prepare_vec_float_eq = prepare_vec_arith
    prepare_vec_float_ne = prepare_vec_arith
    prepare_vec_int_eq = prepare_vec_arith
    prepare_vec_int_ne = prepare_vec_arith
    prepare_vec_float_xor = prepare_vec_arith
    del prepare_vec_arith


    def prepare_vec_store(self, op):
        descr = op.getdescr()
        assert isinstance(descr, ArrayDescr)
        assert not descr.is_array_of_pointers() and \
               not descr.is_array_of_structs()
        itemsize, ofs, _ = unpack_arraydescr(descr)
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        a2 = op.getarg(2)
        baseloc = self.ensure_reg(a0)
        ofsloc = self.ensure_reg(a1)
        valueloc = self.ensure_vector_reg(a2)

        integer = not (descr.is_array_of_floats() or descr.getconcrete_type() == FLOAT)
        aligned = False
        return [baseloc, ofsloc, valueloc,
                imm(itemsize), imm(ofs), imm(integer), imm(aligned)]

    def prepare_vec_int_signext(self, op):
        assert isinstance(op, VectorOp)
        a0 = op.getarg(0)
        loc0 = self.ensure_vector_reg(a0)
        resloc = self.force_allocate_vector_reg(op)
        return [resloc, loc0]

    def prepare_vec_arith_unary(self, op):
        a0 = op.getarg(0)
        loc0 = self.ensure_vector_reg(a0)
        resloc = self.force_allocate_vector_reg(op)
        sizeloc = imm(op.bytesize)
        return [resloc, loc0, sizeloc]

    prepare_vec_float_neg = prepare_vec_arith_unary
    prepare_vec_float_abs = prepare_vec_arith_unary
    del prepare_vec_arith_unary

    def prepare_vec_pack_i(self, op):
        # new_res = vec_pack_i(res, src, index, count)
        assert isinstance(op, VectorOp)
        arg = op.getarg(1)
        index = op.getarg(2)
        count = op.getarg(3)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        vloc = self.ensure_vector_reg(op.getarg(0))
        srcloc = self.ensure_reg(arg)
        resloc = self.force_allocate_vector_reg(op)
        residx = index.value # where to put it in result?
        srcidx = 0
        return [resloc, vloc, srcloc, imm(residx), imm(srcidx), imm(count.value)]

    def prepare_vec_pack_f(self, op):
        # new_res = vec_pack_i(res, src, index, count)
        assert isinstance(op, VectorOp)
        arg = op.getarg(1)
        index = op.getarg(2)
        count = op.getarg(3)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        assert not arg.is_vector()
        srcloc = self.ensure_reg(arg)
        vloc = self.ensure_vector_reg(op.getarg(0))
        resloc = self.force_allocate_vector_reg(op)
        residx = index.value # where to put it in result?
        srcidx = 0
        return [resloc, vloc, srcloc, imm(residx), imm(srcidx), imm(count.value)]

    def prepare_vec_unpack_f(self, op):
        index = op.getarg(1)
        count = op.getarg(2)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        srcloc = self.ensure_vector_reg(op.getarg(0))
        resloc = self.force_allocate_reg(op)
        return [resloc, srcloc, imm(index.value), imm(count.value)]

    def prepare_vec_unpack_i(self, op):
        assert isinstance(op, VectorOp)
        index = op.getarg(1)
        count = op.getarg(2)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        arg = op.getarg(0)
        if arg.is_vector():
            srcloc = self.ensure_vector_reg(op.getarg(0))
        else:
            srcloc = self.ensure_reg(op.getarg(0))
        resloc = self.force_allocate_reg(op)
        return [resloc, srcloc, imm(index.value), imm(count.value)]

    def expand_float(self, size, box):
        adr = self.assembler.datablockwrapper.malloc_aligned(16, 16)
        fs = box.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = fs
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[1] = fs
        return l.ConstFloatLoc(adr)

    def prepare_vec_expand_f(self, op):
        arg = op.getarg(0)
        if arg.is_constant():
            l0 = self.expand_float(op.bytesize, arg)
            res = self.force_allocate_vector_reg(op)
        else:
            l0 = self.ensure_reg(arg)
            res = self.force_allocate_vector_reg(op)
        return [res, l0]

    def prepare_vec_expand_i(self, op):
        arg = op.getarg(0)
        mc = self.assembler.mc
        if arg.is_constant():
            l0 = self.rm.get_scratch_reg()
            mc.load_imm(l0, arg.value)
        else:
            l0 = self.ensure_reg(arg)
        mc.store(l0.value, r.SP.value, PARAM_SAVE_AREA_OFFSET)
        size = op.bytesize
        if size == 8:
            mc.store(l0.value, r.SP.value, PARAM_SAVE_AREA_OFFSET+8)
        res = self.force_allocate_vector_reg(op)
        return [res, l0, imm(PARAM_SAVE_AREA_OFFSET)]

    def prepare_vec_int_is_true(self, op):
        arg = op.getarg(0)
        assert isinstance(arg, VectorOp)
        argloc = self.ensure_vector_reg(arg)
        resloc = self.force_allocate_vector_reg(op)
        return [resloc, argloc, imm(arg.bytesize)]

    def _prepare_vec(self, op):
        # pseudo instruction, needed to allocate a register for a new variable
        return [self.force_allocate_vector_reg(op)]

    prepare_vec_i = _prepare_vec
    prepare_vec_f = _prepare_vec

    def prepare_vec_cast_float_to_int(self, op):
        l0 = self.ensure_vector_reg(op.getarg(0))
        res = self.force_allocate_vector_reg(op)
        return [res, l0]

    prepare_vec_cast_int_to_float = prepare_vec_cast_float_to_int

    def load_vector_condition_into_cc(self, box):
        if self.assembler.guard_success_cc == c.cond_none:
            # compare happended before
            #loc = self.ensure_reg(box)
            #mc = self.assembler.mc
            #mc.cmp_op(0, loc.value, 0, imm=True)
            self.assembler.guard_success_cc = c.NE

    def prepare_vec_guard_true(self, op):
        self.load_vector_condition_into_cc(op.getarg(0))
        return self._prepare_guard(op)

    def prepare_vec_guard_false(self, op):
        self.load_vector_condition_into_cc(op.getarg(0))
        return self._prepare_guard(op)

