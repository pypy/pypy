from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.history import ConstInt
from rpython.jit.metainterp.history import CONST_NULL
from rpython.jit.metainterp.optimizeopt import info, optimizer
from rpython.jit.metainterp.optimizeopt.optimizer import REMOVED
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method

from rpython.jit.metainterp.optimizeopt.rawbuffer import InvalidRawOperation
from rpython.jit.metainterp.resoperation import rop, ResOperation


class OptVirtualize(optimizer.Optimization):
    "Virtualize objects until they escape."

    _last_guard_not_forced_2 = None

    def make_virtual(self, known_class, source_op, descr):
        opinfo = info.InstancePtrInfo(descr, known_class, is_virtual=True)
        opinfo.init_fields(descr, 0)
        newop = self.replace_op_with(source_op, source_op.getopnum())
        newop.set_forwarded(opinfo)
        return opinfo

    def make_varray(self, arraydescr, size, source_op, clear=False):
        if arraydescr.is_array_of_structs():
            assert clear
            opinfo = info.ArrayStructInfo(arraydescr, size, is_virtual=True)
        else:
            const = self.new_const_item(arraydescr)
            opinfo = info.ArrayPtrInfo(arraydescr, const, size, clear,
                                       is_virtual=True)
        # Replace 'source_op' with a version in which the length is
        # given as directly a Const, without relying on forwarding.
        # See test_virtual_array_length_discovered_constant_2.
        newop = self.replace_op_with(source_op, source_op.getopnum(),
                                     args=[ConstInt(size)])
        newop.set_forwarded(opinfo)
        return opinfo

    def make_vstruct(self, structdescr, source_op):
        opinfo = info.StructPtrInfo(structdescr, is_virtual=True)
        opinfo.init_fields(structdescr, 0)
        newop = self.replace_op_with(source_op, source_op.getopnum())
        newop.set_forwarded(opinfo)
        return opinfo

    def make_virtual_raw_memory(self, size, source_op):
        opinfo = info.RawBufferPtrInfo(self.optimizer.cpu, size)
        newop = self.replace_op_with(source_op, source_op.getopnum(),
                                     args=[source_op.getarg(0), ConstInt(size)])
        newop.set_forwarded(opinfo)
        return opinfo

    def make_virtual_raw_slice(self, offset, parent, source_op):
        opinfo = info.RawSlicePtrInfo(offset, parent)
        newop = self.replace_op_with(source_op, source_op.getopnum(),
                                   args=[source_op.getarg(0), ConstInt(offset)])
        newop.set_forwarded(opinfo)
        return opinfo

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            return
        self.emit_operation(op)

    def optimize_GUARD_NOT_FORCED(self, op):
        if self.last_emitted_operation is REMOVED:
            return
        self.emit_operation(op)

    def optimize_GUARD_NOT_FORCED_2(self, op):
        self._last_guard_not_forced_2 = op

    def optimize_FINISH(self, op):
        if self._last_guard_not_forced_2 is not None:
            guard_op = self._last_guard_not_forced_2
            self.emit_operation(op)
            guard_op = self.optimizer.store_final_boxes_in_guard(guard_op, [])
            i = len(self.optimizer._newoperations) - 1
            assert i >= 0
            self.optimizer._newoperations.insert(i, guard_op)
        else:
            self.emit_operation(op)

    def optimize_CALL_MAY_FORCE_I(self, op):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_JIT_FORCE_VIRTUAL:
            if self._optimize_JIT_FORCE_VIRTUAL(op):
                return
        self.emit_operation(op)
    optimize_CALL_MAY_FORCE_R = optimize_CALL_MAY_FORCE_I
    optimize_CALL_MAY_FORCE_F = optimize_CALL_MAY_FORCE_I
    optimize_CALL_MAY_FORCE_N = optimize_CALL_MAY_FORCE_I

    def optimize_COND_CALL(self, op):
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_JIT_FORCE_VIRTUALIZABLE:
            opinfo = self.getptrinfo(op.getarg(2))
            if opinfo and opinfo.is_virtual():
                return
        self.emit_operation(op)

    def optimize_VIRTUAL_REF(self, op):
        # get some constants
        vrefinfo = self.optimizer.metainterp_sd.virtualref_info
        c_cls = vrefinfo.jit_virtual_ref_const_class
        vref_descr = vrefinfo.descr
        descr_virtual_token = vrefinfo.descr_virtual_token
        descr_forced = vrefinfo.descr_forced
        #
        # Replace the VIRTUAL_REF operation with a virtual structure of type
        # 'jit_virtual_ref'.  The jit_virtual_ref structure may be forced soon,
        # but the point is that doing so does not force the original structure.
        newop = ResOperation(rop.NEW_WITH_VTABLE, [], descr=vref_descr)
        vrefvalue = self.make_virtual(c_cls, newop, vref_descr)
        op.set_forwarded(newop)
        newop.set_forwarded(vrefvalue)
        token = ResOperation(rop.FORCE_TOKEN, [])
        self.emit_operation(token)
        vrefvalue.setfield(descr_virtual_token, newop, token)
        vrefvalue.setfield(descr_forced, newop,
                           self.optimizer.cpu.ts.CONST_NULLREF)

    def optimize_VIRTUAL_REF_FINISH(self, op):
        # This operation is used in two cases.  In normal cases, it
        # is the end of the frame, and op.getarg(1) is NULL.  In this
        # case we just clear the vref.virtual_token, because it contains
        # a stack frame address and we are about to leave the frame.
        # In that case vref.forced should still be NULL, and remains
        # NULL; and accessing the frame through the vref later is
        # *forbidden* and will raise InvalidVirtualRef.
        #
        # In the other (uncommon) case, the operation is produced
        # earlier, because the vref was forced during tracing already.
        # In this case, op.getarg(1) is the virtual to force, and we
        # have to store it in vref.forced.
        #
        vrefinfo = self.optimizer.metainterp_sd.virtualref_info
        seo = self.optimizer.send_extra_operation

        # - set 'forced' to point to the real object
        objbox = op.getarg(1)
        if not CONST_NULL.same_constant(objbox):
            seo(ResOperation(rop.SETFIELD_GC, op.getarglist(),
                             descr=vrefinfo.descr_forced))

        # - set 'virtual_token' to TOKEN_NONE (== NULL)
        args = [op.getarg(0), CONST_NULL]
        seo(ResOperation(rop.SETFIELD_GC, args,
                         descr=vrefinfo.descr_virtual_token))
        # Note that in some cases the virtual in op.getarg(1) has been forced
        # already.  This is fine.  In that case, and *if* a residual
        # CALL_MAY_FORCE suddenly turns out to access it, then it will
        # trigger a ResumeGuardForcedDescr.handle_async_forcing() which
        # will work too (but just be a little pointless, as the structure
        # was already forced).

    def _optimize_JIT_FORCE_VIRTUAL(self, op):
        vref = self.getptrinfo(op.getarg(1))
        vrefinfo = self.optimizer.metainterp_sd.virtualref_info
        if vref and vref.is_virtual():
            tokenop = vref.getfield(vrefinfo.descr_virtual_token, None)
            if tokenop is None:
                return False
            tokeninfo = self.getptrinfo(tokenop)
            if (tokeninfo is not None and tokeninfo.is_constant() and
                    not tokeninfo.is_nonnull()):
                forcedop = vref.getfield(vrefinfo.descr_forced, None)
                forcedinfo = self.getptrinfo(forcedop)
                if forcedinfo is not None and not forcedinfo.is_null():
                    self.make_equal_to(op, forcedop)
                    self.last_emitted_operation = REMOVED
                    return True
        return False

    def optimize_GETFIELD_GC_I(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            fieldop = opinfo.getfield(op.getdescr())
            if fieldop is None:
                fieldop = self.optimizer.new_const(op.getdescr())
            self.make_equal_to(op, fieldop)
        else:
            self.make_nonnull(op.getarg(0))
            self.emit_operation(op)
    optimize_GETFIELD_GC_R = optimize_GETFIELD_GC_I
    optimize_GETFIELD_GC_F = optimize_GETFIELD_GC_I

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETFIELD_GC_PURE is_always_pure().
    optimize_GETFIELD_GC_PURE_I = optimize_GETFIELD_GC_I
    optimize_GETFIELD_GC_PURE_R = optimize_GETFIELD_GC_I
    optimize_GETFIELD_GC_PURE_F = optimize_GETFIELD_GC_I

    def optimize_SETFIELD_GC(self, op):
        struct = op.getarg(0)
        opinfo = self.getptrinfo(struct)
        if opinfo is not None and opinfo.is_virtual():
            opinfo.setfield(op.getdescr(), struct,
                            self.get_box_replacement(op.getarg(1)))
        else:
            self.make_nonnull(struct)
            self.emit_operation(op)

    def optimize_NEW_WITH_VTABLE(self, op):
        known_class = ConstInt(op.getdescr().get_vtable())
        self.make_virtual(known_class, op, op.getdescr())

    def optimize_NEW(self, op):
        self.make_vstruct(op.getdescr(), op)

    def optimize_NEW_ARRAY(self, op):
        sizebox = self.get_constant_box(op.getarg(0))
        if sizebox is not None:
            self.make_varray(op.getdescr(), sizebox.getint(), op)
        else:
            self.emit_operation(op)

    def optimize_NEW_ARRAY_CLEAR(self, op):
        sizebox = self.get_constant_box(op.getarg(0))
        if sizebox is not None:
            self.make_varray(op.getdescr(), sizebox.getint(), op, clear=True)
        else:
            self.emit_operation(op)        

    def optimize_CALL_N(self, op):
        effectinfo = op.getdescr().get_extra_info()
        if effectinfo.oopspecindex == EffectInfo.OS_RAW_MALLOC_VARSIZE_CHAR:
            self.do_RAW_MALLOC_VARSIZE_CHAR(op)
        elif effectinfo.oopspecindex == EffectInfo.OS_RAW_FREE:
            self.do_RAW_FREE(op)
        elif effectinfo.oopspecindex == EffectInfo.OS_JIT_FORCE_VIRTUALIZABLE:
            # we might end up having CALL here instead of COND_CALL
            info = self.getptrinfo(op.getarg(1))
            if info and info.is_virtual():
                return
        else:
            self.emit_operation(op)
    optimize_CALL_R = optimize_CALL_N
    optimize_CALL_I = optimize_CALL_N

    def do_RAW_MALLOC_VARSIZE_CHAR(self, op):
        sizebox = self.get_constant_box(op.getarg(1))
        if sizebox is None:
            self.emit_operation(op)
            return
        self.make_virtual_raw_memory(sizebox.getint(), op)
        self.last_emitted_operation = REMOVED

    def do_RAW_FREE(self, op):
        opinfo = self.getrawptrinfo(op.getarg(1))
        if opinfo and opinfo.is_virtual():
            return
        self.emit_operation(op)

    def optimize_INT_ADD(self, op):
        opinfo = self.getrawptrinfo(op.getarg(0), create=False)
        offsetbox = self.get_constant_box(op.getarg(1))
        if opinfo and opinfo.is_virtual() and offsetbox is not None:
            offset = offsetbox.getint()
            # the following check is constant-folded to False if the
            # translation occurs without any VRawXxxValue instance around
            if (isinstance(opinfo, info.RawBufferPtrInfo) or
                isinstance(opinfo, info.RawSlicePtrInfo)):
                self.make_virtual_raw_slice(offset, opinfo, op)
                return
        self.emit_operation(op)

    def optimize_ARRAYLEN_GC(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            self.make_constant_int(op, opinfo.getlength())
        else:
            self.make_nonnull(op.getarg(0))
            self.emit_operation(op)

    def optimize_GETARRAYITEM_GC_I(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                item = opinfo.getitem(op.getdescr(), indexbox.getint())
                if item is None:   # reading uninitialized array items?
                    assert False, "can't read uninitialized items"
                    itemvalue = value.constvalue     # bah, just return 0
                self.make_equal_to(op, item)
                return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
    optimize_GETARRAYITEM_GC_R = optimize_GETARRAYITEM_GC_I
    optimize_GETARRAYITEM_GC_F = optimize_GETARRAYITEM_GC_I

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETARRAYITEM_GC_PURE is_always_pure().
    optimize_GETARRAYITEM_GC_PURE_I = optimize_GETARRAYITEM_GC_I
    optimize_GETARRAYITEM_GC_PURE_R = optimize_GETARRAYITEM_GC_I
    optimize_GETARRAYITEM_GC_PURE_F = optimize_GETARRAYITEM_GC_I

    def optimize_SETARRAYITEM_GC(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                opinfo.setitem(op.getdescr(), indexbox.getint(),
                               self.get_box_replacement(op.getarg(0)),
                               self.get_box_replacement(op.getarg(2)))
                return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)

    def _unpack_arrayitem_raw_op(self, op, indexbox):
        index = indexbox.getint()
        cpu = self.optimizer.cpu
        descr = op.getdescr()
        basesize, itemsize, _ = cpu.unpack_arraydescr_size(descr)
        offset = basesize + (itemsize*index)
        return offset, itemsize, descr

    def optimize_GETARRAYITEM_RAW_I(self, op):
        opinfo = self.getrawptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                offset, itemsize, descr = self._unpack_arrayitem_raw_op(op,
                                                                indexbox)
                try:
                    itemvalue = opinfo.getitem_raw(offset, itemsize, descr)
                except InvalidRawOperation:
                    pass
                else:
                    self.make_equal_to(op, itemvalue)
                    return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
    optimize_GETARRAYITEM_RAW_F = optimize_GETARRAYITEM_RAW_I

    def optimize_SETARRAYITEM_RAW(self, op):
        opinfo = self.getrawptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                offset, itemsize, descr = self._unpack_arrayitem_raw_op(op, indexbox)
                itemop = self.get_box_replacement(op.getarg(2))
                try:
                    opinfo.setitem_raw(offset, itemsize, descr, itemop)
                    return
                except InvalidRawOperation:
                    pass
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)

    def _unpack_raw_load_store_op(self, op, offsetbox):
        offset = offsetbox.getint()
        cpu = self.optimizer.cpu
        descr = op.getdescr()
        itemsize = cpu.unpack_arraydescr_size(descr)[1]
        return offset, itemsize, descr

    def optimize_RAW_LOAD_I(self, op):
        opinfo = self.getrawptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            offsetbox = self.get_constant_box(op.getarg(1))
            if offsetbox is not None:
                offset, itemsize, descr = self._unpack_raw_load_store_op(op, offsetbox)
                try:
                    itemop = opinfo.getitem_raw(offset, itemsize, descr)
                except InvalidRawOperation:
                    pass
                else:
                    self.make_equal_to(op, itemop)
                    return
        self.emit_operation(op)
    optimize_RAW_LOAD_F = optimize_RAW_LOAD_I

    def optimize_RAW_STORE(self, op):
        opinfo = self.getrawptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            offsetbox = self.get_constant_box(op.getarg(1))
            if offsetbox is not None:
                offset, itemsize, descr = self._unpack_raw_load_store_op(op, offsetbox)
                try:
                    opinfo.setitem_raw(offset, itemsize, descr, op.getarg(2))
                    return
                except InvalidRawOperation:
                    pass
        self.emit_operation(op)

    def optimize_GETINTERIORFIELD_GC_I(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                descr = op.getdescr()
                fld = opinfo.getinteriorfield_virtual(indexbox.getint(), descr)
                if fld is None:
                    raise Exception("I think this is illegal")
                    xxx
                    fieldvalue = self.new_const(descr)
                self.make_equal_to(op, fld)
                return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
    optimize_GETINTERIORFIELD_GC_R = optimize_GETINTERIORFIELD_GC_I
    optimize_GETINTERIORFIELD_GC_F = optimize_GETINTERIORFIELD_GC_I

    def optimize_SETINTERIORFIELD_GC(self, op):
        opinfo = self.getptrinfo(op.getarg(0))
        if opinfo and opinfo.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                opinfo.setinteriorfield_virtual(indexbox.getint(),
                                                op.getdescr(),
                                       self.get_box_replacement(op.getarg(2)))
                return
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)


dispatch_opt = make_dispatcher_method(OptVirtualize, 'optimize_',
        default=OptVirtualize.emit_operation)

OptVirtualize.propagate_forward = dispatch_opt
