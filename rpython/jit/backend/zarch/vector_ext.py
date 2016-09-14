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
from rpython.jit.backend.llsupport.vector_ext import VectorExt
from rpython.jit.backend.zarch.detect_feature import detect_simd_z
import rpython.jit.backend.zarch.registers as r
import rpython.jit.backend.zarch.conditions as c
import rpython.jit.backend.zarch.locations as l
import rpython.jit.backend.zarch.masks as m
from rpython.jit.backend.zarch.locations import imm
from rpython.jit.backend.llsupport.asmmemmgr import MachineDataBlockWrapper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.jit.codewriter import longlong
from rpython.rlib.objectmodel import always_inline

def not_implemented(msg):
    msg = '[zarch/vector_ext] %s\n' % msg
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)

def flush_vec_cc(asm, regalloc, condition, size, resultloc):
    # After emitting an instruction that leaves a boolean result in
    # a condition code (cc), call this.  In the common case, resultloc
    # will be set to SPP by the regalloc, which in this case means
    # "propagate it between this operation and the next guard by keeping
    # it in the cc".  In the uncommon case, resultloc is another
    # register, and we emit a load from the cc into this register.

    if resultloc is r.SPP:
        asm.guard_success_cc = condition
    else:
        ones = regalloc.vrm.get_scratch_reg()
        zeros = regalloc.vrm.get_scratch_reg()
        asm.mc.VX(zeros, zeros, zeros)
        asm.mc.VREPI(ones, l.imm(1), l.itemsize_to_mask(size))
        asm.mc.VSEL(resultloc, ones, zeros, resultloc)

class ZSIMDVectorExt(VectorExt):
    def setup_once(self, asm):
        if detect_simd_z():
            self.enable(16, accum=True)
            asm.setup_once_vector()
        self._setup = True

class VectorAssembler(object):
    _mixin_ = True

    # TODO VEC_DOUBLE_WORD_ONES = 0

    def setup_once_vector(self):
        # TODO if IS_BIG_ENDIAN:
        # TODO     # 2x 64 bit signed integer(1) BE
        # TODO     data = (b'\x00' * 7 + b'\x01') * 2
        # TODO else:
        # TODO     # 2x 64 bit signed integer(1) LE
        # TODO     data = (b'\x01' + b'\x00' * 7) * 2
        # TODO datablockwrapper = MachineDataBlockWrapper(self.cpu.asmmemmgr, [])
        # TODO mem = datablockwrapper.malloc_aligned(len(data), alignment=16)
        # TODO datablockwrapper.done()
        # TODO addr = rffi.cast(rffi.CArrayPtr(lltype.Char), mem)
        # TODO for i in range(len(data)):
        # TODO     addr[i] = data[i]
        # TODO self.VEC_DOUBLE_WORD_ONES = mem
        pass

    def emit_vec_load_f(self, op, arglocs, regalloc):
        resloc, baseloc, indexloc, size_loc, offsetloc, integer_loc = arglocs
        addrloc = self._load_address(baseloc, indexloc, offsetloc)
        self.mc.VL(resloc, addrloc)

    emit_vec_load_i = emit_vec_load_f

    def emit_vec_store(self, op, arglocs, regalloc):
        baseloc, indexloc, valueloc, sizeloc, offsetloc, integer_loc = arglocs
        addrloc = self._load_address(baseloc, indexloc, offsetloc)
        self.mc.VST(valueloc, addrloc)

    def emit_vec_int_add(self, op, arglocs, regalloc):
        resloc, loc0, loc1, size_loc = arglocs
        size = size_loc.value
        mask = l.itemsize_to_mask(size_loc.value)
        self.mc.VA(resloc, loc0, loc1, mask)

    def emit_vec_int_sub(self, op, arglocs, regalloc):
        resloc, loc0, loc1, size_loc = arglocs
        mask = l.itemsize_to_mask(size_loc.value)
        self.mc.VS(resloc, loc0, loc1, mask)

    def emit_vec_float_add(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 8:
            self.mc.VFA(resloc, loc0, loc1, 3, 0, 0)
            return
        not_implemented("vec_float_add of size %d" % itemsize)

    def emit_vec_float_sub(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 8:
            self.mc.VFS(resloc, loc0, loc1, 3, 0, 0)
            return
        not_implemented("vec_float_sub of size %d" % itemsize)

    def emit_vec_float_mul(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 8:
            self.mc.VFM(resloc, loc0, loc1, 3, 0, 0)
            return
        not_implemented("vec_float_mul of size %d" % itemsize)

    def emit_vec_float_truediv(self, op, arglocs, regalloc):
        resloc, loc0, loc1, itemsize_loc = arglocs
        itemsize = itemsize_loc.value
        if itemsize == 8:
            self.mc.VFD(resloc, loc0, loc1, 3, 0, 0)
            return
        not_implemented("vec_float_truediv of size %d" % itemsize)

    def emit_vec_int_and(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.VN(resloc, loc0, loc1)

    def emit_vec_int_or(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.VO(resloc, loc0, loc1)

    def emit_vec_int_xor(self, op, arglocs, regalloc):
        resloc, loc0, loc1, sizeloc = arglocs
        self.mc.VX(resloc, loc0, loc1)

    def emit_vec_int_signext(self, op, arglocs, regalloc):
        resloc, loc0 = arglocs
        # signext is only allowed if the data type sizes do not change.
        # e.g. [byte,byte] = sign_ext([byte, byte]), a simple move is sufficient!
        self.regalloc_mov(loc0, resloc)

    def emit_vec_float_abs(self, op, arglocs, regalloc):
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        if size == 8:
            self.mc.VFPSO(resloc, argloc, 3, 0, 2)
            return
        not_implemented("vec_float_abs of size %d" % itemsize)

    def emit_vec_float_neg(self, op, arglocs, regalloc):
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        if size == 8:
            self.mc.VFPSO(resloc, argloc, 3, 0, 0)
            return
        not_implemented("vec_float_abs of size %d" % itemsize)

    def emit_vec_guard_true(self, guard_op, arglocs, regalloc):
        self._emit_guard(guard_op, arglocs)

    def emit_vec_guard_false(self, guard_op, arglocs, regalloc):
        self.guard_success_cc = c.negate(self.guard_success_cc)
        self._emit_guard(guard_op, arglocs)

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

    def emit_vec_int_is_true(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        # TODO
        resloc, argloc, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.vrm.get_scratch_reg(type=INT).value
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
        flush_vec_cc(self, regalloc, c.VNEI, op.bytesize, resloc)

    def emit_vec_float_eq(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        resloc, loc0, loc1, sizeloc = arglocs
        size = sizeloc.value
        if size == 8:
            # bit 3 in last argument sets the condition code
            self.mc.VFCE(resloc, loc0, loc1, 3, 0, 1)
        else:
            not_implemented("[zarch/assembler] float == for size %d" % size)
        flush_vec_cc(self, regalloc, c.VEQI, op.bytesize, resloc)

    def emit_vec_float_xor(self, op, arglocs, regalloc):
        resloc, l0, l1, sizeloc = arglocs
        res = resloc.value
        r0 = l0.value
        r1 = l1.value
        self.mc.xxlxor(res, r0, r1)

    def emit_vec_float_ne(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
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
            not_implemented("float == for size %d" % size)
        res = resloc.value
        self.mc.lvx(res, off, r.SP.value)
        self.mc.vnor(res, res, res) # complement
        flush_vec_cc(self, regalloc, c.VNEI, op.bytesize, resloc)

    def emit_vec_cast_int_to_float(self, op, arglocs, regalloc):
        resloc, loc0 = arglocs
        offloc = regalloc.rm.get_scratch_reg()
        off = offloc.value
        # SP is always 16 byte aligned, and PARAM_SAVE_AREA_OFFSET % 16 == 0
        # bit 1 on mask4 -> supresses inexact exception
        self.mc.VCDG(resloc, loc0, 3, 4, m.RND_TOZERO.value)
        #self.mc.load_imm(offloc, PARAM_SAVE_AREA_OFFSET)
        #self.mc.stvx(l0.value, off, r.SP.value)
        #self.mc.lxvd2x(res.value, off, r.SP.value)
        #self.mc.xvcvsxddp(res.value, res.value)

    def emit_vec_int_eq(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
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
        flush_vec_cc(self, regalloc, c.VEQI, op.bytesize, res)

    def emit_vec_int_ne(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        res, l0, l1, sizeloc = arglocs
        size = sizeloc.value
        tmp = regalloc.vrm.get_scratch_reg(type=INT).value
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
        flush_vec_cc(self, regalloc, c.VEQI, op.bytesize, res)

    def emit_vec_cast_float_to_int(self, op, arglocs, regalloc):
        res, l0 = arglocs
        offloc = regalloc.rm.get_scratch_reg()
        v0 = regalloc.vrm.get_scratch_reg(type=INT)
        off = offloc.value
        # SP is always 16 byte aligned, and PARAM_SAVE_AREA_OFFSET % 16 == 0
        self.mc.load_imm(offloc, PARAM_SAVE_AREA_OFFSET)
        self.mc.xvcvdpsxds(res.value, l0.value)

    def emit_vec_expand_f(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
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
            not_implemented("vec expand in this combination not supported")

    def emit_vec_expand_i(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
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
            not_implemented("expand int size not impl")

    def emit_vec_pack_i(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        resultloc, vloc, sourceloc, residxloc, srcidxloc, countloc = arglocs
        srcidx = srcidxloc.value
        residx = residxloc.value
        count = countloc.value
        res = resultloc.value
        vector = vloc.value
        src = sourceloc.value
        size = op.bytesize
        assert resultloc.is_vector_reg() # vector <- reg
        self.mc.load_imm(r.SCRATCH2, PARAM_SAVE_AREA_OFFSET)
        self.mc.stvx(vector, r.SCRATCH2.value, r.SP.value)
        idx = residx
        if size == 8:
            if not IS_BIG_ENDIAN:
                idx = (16 // size) - 1 - idx
            self.mc.store(src, r.SP.value, PARAM_SAVE_AREA_OFFSET+8*idx)
        elif size == 4:
            for j in range(count):
                idx = j + residx
                if not IS_BIG_ENDIAN:
                    idx = (16 // size) - 1 - idx
                self.mc.stw(src, r.SP.value, PARAM_SAVE_AREA_OFFSET+4*idx)
        elif size == 2:
            for j in range(count):
                idx = j + residx
                if not IS_BIG_ENDIAN:
                    idx = (16 // size) - 1 - idx
                self.mc.sth(src, r.SP.value, PARAM_SAVE_AREA_OFFSET+2*idx)
        elif size == 1:
            for j in range(count):
                idx = j + residx
                if not IS_BIG_ENDIAN:
                    idx = (16 // size) - 1 - idx
                self.mc.stb(src, r.SP.value, PARAM_SAVE_AREA_OFFSET+idx)
        self.mc.lvx(res, r.SCRATCH2.value, r.SP.value)

    def emit_vec_unpack_i(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        resloc, srcloc, idxloc, countloc, sizeloc = arglocs
        idx = idxloc.value
        res = resloc.value
        src = srcloc.value
        size = sizeloc.value
        count = countloc.value
        if count == 1:
            assert srcloc.is_vector_reg()
            assert not resloc.is_vector_reg()
            off = PARAM_SAVE_AREA_OFFSET
            self.mc.load_imm(r.SCRATCH2, off)
            self.mc.stvx(src, r.SCRATCH2.value, r.SP.value)
            if not IS_BIG_ENDIAN:
                idx = (16 // size) - 1 - idx
            off += size * idx
            if size == 8:
                self.mc.load(res, r.SP.value, off)
                return
            elif size == 4:
                self.mc.lwa(res, r.SP.value, off)
                return
            elif size == 2:
                self.mc.lha(res, r.SP.value, off)
                return
            elif size == 1:
                self.mc.lbz(res, r.SP.value, off)
                self.mc.extsb(res, res)
                return
        else:
            # count is not 1, but only 2 is supported for i32
            # 4 for i16 and 8 for i8.
            src = srcloc.value
            res = resloc.value

            self.mc.load_imm(r.SCRATCH2, PARAM_SAVE_AREA_OFFSET)
            self.mc.stvx(src, r.SCRATCH2.value, r.SP.value)
            self.mc.load_imm(r.SCRATCH2, PARAM_SAVE_AREA_OFFSET+16)
            self.mc.stvx(res, r.SCRATCH2.value, r.SP.value)
            if count * size == 8:
                if not IS_BIG_ENDIAN:
                    endian_off = 8
                off = PARAM_SAVE_AREA_OFFSET
                off = off + endian_off - (idx * size)
                assert idx * size + 8 <= 16
                self.mc.load(r.SCRATCH.value, r.SP.value, off)
                self.mc.store(r.SCRATCH.value, r.SP.value, PARAM_SAVE_AREA_OFFSET+16+endian_off)
                self.mc.lvx(res, r.SCRATCH2.value, r.SP.value)
                return

        not_implemented("%d bit integer, count %d" % \
                       (size*8, count))

    def emit_vec_pack_f(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        resloc, vloc, srcloc, residxloc, srcidxloc, countloc = arglocs
        vec = vloc.value
        res = resloc.value
        src = srcloc.value
        count = countloc.value
        residx = residxloc.value
        srcidx = srcidxloc.value
        size = op.bytesize
        # srcloc is always a floating point register f, this means it is
        # vsr[0] == valueof(f)
        if srcidx == 0:
            if residx == 0:
                # r = (s[0], v[1])
                self.mc.xxpermdi(res, src, vec, permi(0,1))
            else:
                assert residx == 1
                # r = (v[0], s[0])
                self.mc.xxpermdi(res, vec, src, permi(1,1))
        else:
            assert srcidx == 1
            if residx == 0:
                # r = (s[1], v[1])
                self.mc.xxpermdi(res, src, vec, permi(1,1))
            else:
                assert residx == 1
                # r = (v[0], s[1])
                self.mc.xxpermdi(res, vec, src, permi(0,1))

    def emit_vec_unpack_f(self, op, arglocs, regalloc):
        assert isinstance(op, VectorOp)
        resloc, srcloc, srcidxloc, countloc = arglocs
        res = resloc.value
        src = srcloc.value
        srcidx = srcidxloc.value
        size = op.bytesize
        # srcloc is always a floating point register f, this means it is
        # vsr[0] == valueof(f)
        if srcidx == 0:
            # r = (s[0], s[1])
            self.mc.xxpermdi(res, src, src, permi(0,1))
            return
        else:
            # r = (s[1], s[0])
            self.mc.xxpermdi(res, src, src, permi(1,0))
            return
        not_implemented("unpack for combination src %d -> res %d" % (srcidx, residx))

    def _accum_reduce(self, op, arg, accumloc, targetloc):
        # Currently the accumulator can ONLY be the biggest
        # 64 bit float/int
        # TODO
        tgt = targetloc.value
        acc = accumloc.value
        if arg.type == FLOAT:
            # r = (r[0]+r[1],r[0]+r[1])
            if IS_BIG_ENDIAN:
                self.mc.xxpermdi(tgt, acc, acc, 0b00)
            else:
                self.mc.xxpermdi(tgt, acc, acc, 0b10)
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
                self.mc.mulld(tgt, tgt, acc)
            else:
                not_implemented("sum not implemented")
            return

        not_implemented("reduce sum for %s not impl." % arg)

    def emit_vec_f(self, op, arglocs, regalloc):
        pass
    emit_vec_i = emit_vec_f

class VectorRegalloc(object):
    _mixin_ = True

    def force_allocate_vector_reg(self, op):
        forbidden_vars = self.vrm.temp_boxes
        return self.vrm.force_allocate_reg(op, forbidden_vars)

    def force_allocate_vector_reg_or_cc(self, op):
        assert op.type == INT
        if self.next_op_can_accept_cc(self.operations, self.rm.position):
            # hack: return the SPP location to mean "lives in CC".  This
            # SPP will not actually be used, and the location will be freed
            # after the next op as usual.
            self.rm.force_allocate_frame_reg(op)
            return r.SPP
        else:
            return self.force_allocate_vector_reg(op)

    def ensure_vector_reg(self, box):
        return self.vrm.make_sure_var_in_reg(box,
                           forbidden_vars=self.vrm.temp_boxes)

    def _prepare_load(self, op):
        descr = op.getdescr()
        assert isinstance(descr, ArrayDescr)
        assert not descr.is_array_of_pointers() and \
               not descr.is_array_of_structs()
        itemsize, ofs, _ = unpack_arraydescr(descr)
        integer = not (descr.is_array_of_floats() or descr.getconcrete_type() == FLOAT)
        args = op.getarglist()
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        base_loc = self.ensure_reg(a0)
        ofs_loc = self.ensure_reg(a1)
        result_loc = self.force_allocate_vector_reg(op)
        return [result_loc, base_loc, ofs_loc, imm(itemsize), imm(ofs),
                imm(integer)]

    prepare_vec_load_i = _prepare_load
    prepare_vec_load_f = _prepare_load

    def prepare_vec_arith(self, op):
        assert isinstance(op, VectorOp)
        a0 = op.getarg(0)
        a1 = op.getarg(1)
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
    prepare_vec_float_xor = prepare_vec_arith
    del prepare_vec_arith

    def prepare_vec_bool(self, op):
        assert isinstance(op, VectorOp)
        a0 = op.getarg(0)
        a1 = op.getarg(1)
        size = op.bytesize
        args = op.getarglist()
        loc0 = self.ensure_vector_reg(a0)
        loc1 = self.ensure_vector_reg(a1)
        resloc = self.force_allocate_vector_reg_or_cc(op)
        return [resloc, loc0, loc1, imm(size)]

    prepare_vec_float_eq = prepare_vec_bool
    prepare_vec_float_ne = prepare_vec_bool
    prepare_vec_int_eq = prepare_vec_bool
    prepare_vec_int_ne = prepare_vec_bool
    del prepare_vec_bool

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
        return [baseloc, ofsloc, valueloc,
                imm(itemsize), imm(ofs), imm(integer)]

    def prepare_vec_int_signext(self, op):
        assert isinstance(op, VectorOp)
        a0 = op.getarg(0)
        loc0 = self.ensure_vector_reg(a0)
        resloc = self.force_allocate_vector_reg(op)
        return [resloc, loc0]

    def prepare_vec_arith_unary(self, op):
        assert isinstance(op, VectorOp)
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
        # new_res = vec_pack_f(res, src, index, count)
        assert isinstance(op, VectorOp)
        arg = op.getarg(1)
        index = op.getarg(2)
        count = op.getarg(3)
        assert isinstance(index, ConstInt)
        assert isinstance(count, ConstInt)
        assert not arg.is_vector()
        srcloc = self.ensure_reg(arg)
        vloc = self.ensure_vector_reg(op.getarg(0))
        if op.is_vector():
            resloc = self.force_allocate_vector_reg(op)
        else:
            resloc = self.force_allocate_reg(op)
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
            srcloc = self.ensure_vector_reg(arg)
        else:
            # unpack
            srcloc = self.ensure_reg(arg0)
        size = arg.bytesize
        if op.is_vector():
            resloc = self.force_allocate_vector_reg(op)
        else:
            resloc = self.force_allocate_reg(op)
        return [resloc, srcloc, imm(index.value), imm(count.value), imm(size)]

    def expand_float(self, size, box):
        adr = self.assembler.datablockwrapper.malloc_aligned(16, 16)
        fs = box.getfloatstorage()
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[0] = fs
        rffi.cast(rffi.CArrayPtr(longlong.FLOATSTORAGE), adr)[1] = fs
        return l.ConstFloatLoc(adr)

    def prepare_vec_expand_f(self, op):
        assert isinstance(op, VectorOp)
        arg = op.getarg(0)
        if arg.is_constant():
            l0 = self.expand_float(op.bytesize, arg)
            res = self.force_allocate_vector_reg(op)
        else:
            l0 = self.ensure_reg(arg)
            res = self.force_allocate_vector_reg(op)
        return [res, l0]

    def prepare_vec_expand_i(self, op):
        assert isinstance(op, VectorOp)
        arg = op.getarg(0)
        mc = self.assembler.mc
        if arg.is_constant():
            assert isinstance(arg, ConstInt)
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
        assert isinstance(op, VectorOp)
        arg = op.getarg(0)
        assert isinstance(arg, VectorOp)
        argloc = self.ensure_vector_reg(arg)
        resloc = self.force_allocate_vector_reg_or_cc(op)
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

    def prepare_vec_guard_true(self, op):
        self.assembler.guard_success_cc = c.VEQ
        return self._prepare_guard(op)

    def prepare_vec_guard_false(self, op):
        self.assembler.guard_success_cc = c.VNE
