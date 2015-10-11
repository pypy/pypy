import os
from collections import OrderedDict

from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.metainterp.optimizeopt.util import args_dict
from rpython.jit.metainterp.history import Const, ConstInt
from rpython.jit.metainterp.jitexc import JitException
from rpython.jit.metainterp.optimizeopt.optimizer import Optimization, REMOVED
from rpython.jit.metainterp.optimizeopt.util import make_dispatcher_method
from rpython.jit.metainterp.optimizeopt.intutils import IntBound
from rpython.jit.metainterp.optimizeopt.shortpreamble import PreambleOp
from rpython.jit.metainterp.optimize import InvalidLoop
from rpython.jit.metainterp.resoperation import rop, ResOperation, OpHelpers,\
     AbstractResOp, GuardResOp
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.optimizeopt import info
        


class BogusImmutableField(JitException):
    pass


class CachedField(object):
    def __init__(self):
        # Cache information for a field descr, or for an (array descr, index)
        # pair.  It can be in one of two states:
        #
        #   1. 'cached_infos' is a list listing all the infos that are
        #      caching this descr
        #
        #   2. we just did one setfield, which is delayed (and thus
        #      not synchronized).  'lazy_setfield' is the delayed
        #      ResOperation.  In this state, 'cached_infos' contains
        #      out-of-date information.  More precisely, the field
        #      value pending in the ResOperation is *not* visible in
        #      'cached_infos'.
        #
        self.cached_infos = []
        self.cached_structs = []
        self._lazy_setfield = None
        self._lazy_setfield_registered = False

    def register_dirty_field(self, structop, info):
        self.cached_structs.append(structop)
        self.cached_infos.append(info)

    def invalidate(self, descr):
        for opinfo in self.cached_infos:
            assert isinstance(opinfo, info.AbstractStructPtrInfo)
            opinfo._fields[descr.get_index()] = None
        self.cached_infos = []
        self.cached_structs = []

    def produce_potential_short_preamble_ops(self, optimizer, shortboxes,
                                             descr, index=-1):
        assert self._lazy_setfield is None
        for i, info in enumerate(self.cached_infos):
            structbox = optimizer.get_box_replacement(self.cached_structs[i])
            info.produce_short_preamble_ops(structbox, descr, index, optimizer,
                                            shortboxes)

    def possible_aliasing(self, optheap, opinfo):
        # If lazy_setfield is set and contains a setfield on a different
        # structvalue, then we are annoyed, because it may point to either
        # the same or a different structure at runtime.
        # XXX constants?
        return (self._lazy_setfield is not None
                and (not optheap.getptrinfo(
                    self._lazy_setfield.getarg(0)).same_info(opinfo)))

    def do_setfield(self, optheap, op):
        # Update the state with the SETFIELD_GC/SETARRAYITEM_GC operation 'op'.
        structinfo = optheap.ensure_ptr_info_arg0(op)
        arg1 = optheap.get_box_replacement(self._getvalue(op))
        if self.possible_aliasing(optheap, structinfo):
            self.force_lazy_setfield(optheap, op.getdescr())
            assert not self.possible_aliasing(optheap, structinfo)
        cached_field = self._getfield(structinfo, op.getdescr(), optheap, False)
        if cached_field is not None:
            cached_field = optheap.get_box_replacement(cached_field)

        # Hack to ensure constants are imported from the preamble
        # XXX no longer necessary?
        #if cached_fieldvalue and fieldvalue.is_constant():
        #    optheap.optimizer.ensure_imported(cached_fieldvalue)
        #    cached_fieldvalue = self._cached_fields.get(structvalue, None)

        if not cached_field or not cached_field.same_box(arg1):
            # common case: store the 'op' as lazy_setfield, and register
            # myself in the optheap's _lazy_setfields_and_arrayitems list
            self._lazy_setfield = op
            #if not self._lazy_setfield_registered:
            #    self._lazy_setfield_registered = True

        else:
            # this is the case where the pending setfield ends up
            # storing precisely the value that is already there,
            # as proved by 'cached_fields'.  In this case, we don't
            # need any _lazy_setfield: the heap value is already right.
            # Note that this may reset to None a non-None lazy_setfield,
            # cancelling its previous effects with no side effect.
            
            # Now, we have to force the item in the short preamble
            self._getfield(structinfo, op.getdescr(), optheap)
            self._lazy_setfield = None

    def getfield_from_cache(self, optheap, opinfo, descr):
        # Returns the up-to-date field's value, or None if not cached.
        if self.possible_aliasing(optheap, opinfo):
            self.force_lazy_setfield(optheap, descr)
        if self._lazy_setfield is not None:
            op = self._lazy_setfield
            return optheap.get_box_replacement(self._getvalue(op))
        else:
            res = self._getfield(opinfo, descr, optheap)
            if res is not None:
                return res.get_box_replacement()
            return None

    def _getvalue(self, op):
        return op.getarg(1)

    def _getfield(self, opinfo, descr, optheap, true_force=True):
        res = opinfo.getfield(descr, optheap)
        if isinstance(res, PreambleOp):
            if not true_force:
                return res.op
            res = optheap.optimizer.force_op_from_preamble(res)
            opinfo.setfield(descr, None, res, optheap)
        return res

    def force_lazy_setfield(self, optheap, descr, can_cache=True):
        op = self._lazy_setfield
        if op is not None:
            # This is the way _lazy_setfield is usually reset to None.
            # Now we clear _cached_fields, because actually doing the
            # setfield might impact any of the stored result (because of
            # possible aliasing).
            self.invalidate(descr)
            self._lazy_setfield = None
            if optheap.postponed_op:
                for a in op.getarglist():
                    if a is optheap.postponed_op:
                        optheap.emit_postponed_op()
                        break
            optheap.next_optimization.propagate_forward(op)
            if not can_cache:
                return
            # Once it is done, we can put at least one piece of information
            # back in the cache: the value of this particular structure's
            # field.
            opinfo = optheap.ensure_ptr_info_arg0(op)
            self._setfield(op, opinfo, optheap)
        elif not can_cache:
            self.invalidate(descr)

    def _setfield(self, op, opinfo, optheap):
        arg = optheap.get_box_replacement(op.getarg(1))
        struct = optheap.get_box_replacement(op.getarg(0))
        opinfo.setfield(op.getdescr(), struct, arg, optheap, self)

class ArrayCachedField(CachedField):
    def __init__(self, index):
        self.index = index
        CachedField.__init__(self)

    def _getvalue(self, op):
        return op.getarg(2)

    def _getfield(self, opinfo, descr, optheap, true_force=True):
        res = opinfo.getitem(descr, self.index, optheap)
        if (isinstance(res, PreambleOp) and
            optheap.optimizer.cpu.supports_guard_gc_type):
            if not true_force:
                return res.op
            index = res.preamble_op.getarg(1).getint()
            res = optheap.optimizer.force_op_from_preamble(res)
            opinfo.setitem(descr, index, None, res, optheap=optheap)
        return res

    def _setfield(self, op, opinfo, optheap):
        arg = optheap.get_box_replacement(op.getarg(2))
        struct = optheap.get_box_replacement(op.getarg(0))
        opinfo.setitem(op.getdescr(), self.index, struct, arg, self, optheap)

    def invalidate(self, descr):
        for opinfo in self.cached_infos:
            assert isinstance(opinfo, info.ArrayPtrInfo)
            opinfo._items = None
        self.cached_infos = []
        self.cached_structs = []

class OptHeap(Optimization):
    """Cache repeated heap accesses"""

    def __init__(self):
        # mapping descr -> CachedField
        self.cached_fields = OrderedDict()
        self.cached_arrayitems = OrderedDict()

        self.postponed_op = None

        # XXXX the rest is old
        # cached array items:  {array descr: {index: CachedField}}
        #self.cached_arrayitems = {}
        # cached dict items: {dict descr: {(optval, index): box-or-const}}
        self.cached_dict_reads = {}
        # cache of corresponding {array descrs: dict 'entries' field descr}
        self.corresponding_array_descrs = {}
        #
        self._lazy_setfields_and_arrayitems = []
        self._remove_guard_not_invalidated = False
        self._seen_guard_not_invalidated = False

    def setup(self):
        self.optimizer.optheap = self
        # mapping const value -> info corresponding to it's heap cache
        self.const_infos = self.optimizer.cpu.ts.new_ref_dict()

    def flush(self):
        self.cached_dict_reads.clear()
        self.corresponding_array_descrs.clear()
        self.force_all_lazy_setfields_and_arrayitems()
        self.emit_postponed_op()

    def emit_postponed_op(self):
        if self.postponed_op:
            postponed_op = self.postponed_op
            self.postponed_op = None
            self.next_optimization.propagate_forward(postponed_op)

    def produce_potential_short_preamble_ops(self, sb):
        descrkeys = self.cached_fields.keys()
        if not we_are_translated():
            # XXX Pure operation of boxes that are cached in several places will
            #     only be removed from the peeled loop when red from the first
            #     place discovered here. This is far from ideal, as it makes
            #     the effectiveness of our optimization a bit random. It should
            #     howevere always generate correct results. For tests we dont
            #     want this randomness.
            descrkeys.sort(key=str, reverse=True)
        for descr in descrkeys:
            d = self.cached_fields[descr]
            d.produce_potential_short_preamble_ops(self.optimizer, sb, descr)

        for descr, submap in self.cached_arrayitems.items():
            for index, d in submap.items():
                d.produce_potential_short_preamble_ops(self.optimizer, sb,
                                                       descr, index)

    def register_dirty_field(self, descr, op, info):
        self.field_cache(descr).register_dirty_field(op, info)

    def register_dirty_array_field(self, arraydescr, op, index, info):
        self.arrayitem_cache(arraydescr, index).register_dirty_field(op, info)

    def clean_caches(self):
        del self._lazy_setfields_and_arrayitems[:]
        items = self.cached_fields.items()
        if not we_are_translated():
            items.sort(key=str, reverse=True)
        for descr, cf in items:
            if not descr.is_always_pure():
                cf.invalidate(descr)
        for descr, submap in self.cached_arrayitems.iteritems():
            if not descr.is_always_pure():
                for index, cf in submap.iteritems():
                    cf.invalidate(None)
        #self.cached_arrayitems.clear()
        self.cached_dict_reads.clear()

    def field_cache(self, descr):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            cf = self.cached_fields[descr] = CachedField()
        return cf

    def arrayitem_cache(self, descr, index):
        try:
            submap = self.cached_arrayitems[descr]
        except KeyError:
            submap = self.cached_arrayitems[descr] = {}
        try:
            cf = submap[index]
        except KeyError:
            cf = submap[index] = ArrayCachedField(index)
        return cf

    def emit_operation(self, op):        
        self.emitting_operation(op)
        self.emit_postponed_op()
        if (op.is_comparison() or op.is_call_may_force()
            or op.is_ovf()):
            self.postponed_op = op
        else:
            Optimization.emit_operation(self, op)

    def emitting_operation(self, op):
        if op.has_no_side_effect():
            return
        if op.is_ovf():
            return
        if op.is_guard():
            self.optimizer.pendingfields = (
                self.force_lazy_setfields_and_arrayitems_for_guard())
            return
        opnum = op.getopnum()
        if (opnum == rop.SETFIELD_GC or          # handled specially
            opnum == rop.SETFIELD_RAW or         # no effect on GC struct/array
            opnum == rop.SETARRAYITEM_GC or      # handled specially
            opnum == rop.SETARRAYITEM_RAW or     # no effect on GC struct
            opnum == rop.SETINTERIORFIELD_RAW or # no effect on GC struct
            opnum == rop.RAW_STORE or            # no effect on GC struct
            opnum == rop.STRSETITEM or           # no effect on GC struct/array
            opnum == rop.UNICODESETITEM or       # no effect on GC struct/array
            opnum == rop.DEBUG_MERGE_POINT or    # no effect whatsoever
            opnum == rop.JIT_DEBUG or            # no effect whatsoever
            opnum == rop.ENTER_PORTAL_FRAME or   # no effect whatsoever
            opnum == rop.LEAVE_PORTAL_FRAME or   # no effect whatsoever
            opnum == rop.COPYSTRCONTENT or       # no effect on GC struct/array
            opnum == rop.COPYUNICODECONTENT):    # no effect on GC struct/array
            return
        if op.is_call():
            if op.is_call_assembler():
                self._seen_guard_not_invalidated = False
            else:
                effectinfo = op.getdescr().get_extra_info()
                if effectinfo.check_can_invalidate():
                    self._seen_guard_not_invalidated = False
                if not effectinfo.has_random_effects():
                    self.force_from_effectinfo(effectinfo)
                    return
        self.force_all_lazy_setfields_and_arrayitems()
        self.clean_caches()

    def optimize_CALL_I(self, op):
        # dispatch based on 'oopspecindex' to a method that handles
        # specifically the given oopspec call.  For non-oopspec calls,
        # oopspecindex is just zero.
        effectinfo = op.getdescr().get_extra_info()
        oopspecindex = effectinfo.oopspecindex
        if oopspecindex == EffectInfo.OS_DICT_LOOKUP:
            if self._optimize_CALL_DICT_LOOKUP(op):
                return
        self.emit_operation(op)
    optimize_CALL_F = optimize_CALL_I
    optimize_CALL_R = optimize_CALL_I
    optimize_CALL_N = optimize_CALL_I

    def _optimize_CALL_DICT_LOOKUP(self, op):
        # Cache consecutive lookup() calls on the same dict and key,
        # depending on the 'flag_store' argument passed:
        # FLAG_LOOKUP: always cache and use the cached result.
        # FLAG_STORE:  don't cache (it might return -1, which would be
        #                incorrect for future lookups); but if found in
        #                the cache and the cached value was already checked
        #                non-negative, then we can reuse it.
        # FLAG_DELETE: never cache, never use the cached result (because
        #                if there is a cached result, the FLAG_DELETE call
        #                is needed for its side-effect of removing it).
        #                In theory we could cache a -1 for the case where
        #                the delete is immediately followed by a lookup,
        #                but too obscure.
        #
        from rpython.rtyper.lltypesystem.rordereddict import FLAG_LOOKUP
        from rpython.rtyper.lltypesystem.rordereddict import FLAG_STORE
        flag_value = self.getintbound(op.getarg(4))
        if not flag_value.is_constant():
            return False
        flag = flag_value.getint()
        if flag != FLAG_LOOKUP and flag != FLAG_STORE:
            return False
        #
        descrs = op.getdescr().get_extra_info().extradescrs
        assert descrs        # translation hint
        descr1 = descrs[0]
        try:
            d = self.cached_dict_reads[descr1]
        except KeyError:
            d = self.cached_dict_reads[descr1] = args_dict()
            self.corresponding_array_descrs[descrs[1]] = descr1
        #
        key = [self.optimizer.get_box_replacement(op.getarg(1)),   # dict
               self.optimizer.get_box_replacement(op.getarg(2))]   # key
               # other args can be ignored here (hash, store_flag)
        try:
            res_v = d[key]
        except KeyError:
            if flag == FLAG_LOOKUP:
                d[key] = op
            return False
        else:
            if flag != FLAG_LOOKUP:
                if not self.getintbound(res_v).known_ge(IntBound(0, 0)):
                    return False
            self.make_equal_to(op, res_v)
            self.last_emitted_operation = REMOVED
            return True

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if self.last_emitted_operation is REMOVED:
            return
        self.emit_operation(op)

    optimize_GUARD_EXCEPTION = optimize_GUARD_NO_EXCEPTION

    def force_from_effectinfo(self, effectinfo):
        # XXX we can get the wrong complexity here, if the lists
        # XXX stored on effectinfo are large
        for fielddescr in effectinfo.readonly_descrs_fields:
            self.force_lazy_setfield(fielddescr)
        for arraydescr in effectinfo.readonly_descrs_arrays:
            self.force_lazy_setarrayitem(arraydescr)
        for fielddescr in effectinfo.write_descrs_fields:
            if fielddescr.is_always_pure():
                continue
            try:
                del self.cached_dict_reads[fielddescr]
            except KeyError:
                pass
            self.force_lazy_setfield(fielddescr, can_cache=False)
        for arraydescr in effectinfo.write_descrs_arrays:
            self.force_lazy_setarrayitem(arraydescr, can_cache=False)
            if arraydescr in self.corresponding_array_descrs:
                dictdescr = self.corresponding_array_descrs.pop(arraydescr)
                try:
                    del self.cached_dict_reads[dictdescr]
                except KeyError:
                    pass # someone did it already
        if effectinfo.check_forces_virtual_or_virtualizable():
            vrefinfo = self.optimizer.metainterp_sd.virtualref_info
            self.force_lazy_setfield(vrefinfo.descr_forced)
            # ^^^ we only need to force this field; the other fields
            # of virtualref_info and virtualizable_info are not gcptrs.

    def force_lazy_setfield(self, descr, can_cache=True):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            return
        cf.force_lazy_setfield(self, descr, can_cache)

    def force_lazy_setarrayitem(self, arraydescr, indexb=None, can_cache=True):
        try:
            submap = self.cached_arrayitems[arraydescr]
        except KeyError:
            return
        for idx, cf in submap.iteritems():
            if indexb is None or indexb.contains(idx):
                cf.force_lazy_setfield(self, None, can_cache)

    def force_all_lazy_setfields_and_arrayitems(self):
        items = self.cached_fields.items()
        if not we_are_translated():
            items.sort(key=str, reverse=True)
        for descr, cf in items:
            cf.force_lazy_setfield(self, descr)
        for submap in self.cached_arrayitems.itervalues():
            for index, cf in submap.iteritems():
                cf.force_lazy_setfield(self, None)

    def force_lazy_setfields_and_arrayitems_for_guard(self):
        pendingfields = []
        items = self.cached_fields.items()
        if not we_are_translated():
            items.sort(key=str, reverse=True)
        for descr, cf in items:
            op = cf._lazy_setfield
            if op is None:
                continue
            val = op.getarg(1)
            if self.optimizer.is_virtual(val):
                pendingfields.append(op)
                continue
            cf.force_lazy_setfield(self, descr)
        for descr, submap in self.cached_arrayitems.iteritems():
            for index, cf in submap.iteritems():
                op = cf._lazy_setfield
                if op is None:
                    continue
                # the only really interesting case that we need to handle in the
                # guards' resume data is that of a virtual object that is stored
                # into a field of a non-virtual object.  Here, 'op' in either
                # SETFIELD_GC or SETARRAYITEM_GC.
                opinfo = self.getptrinfo(op.getarg(0))
                assert not opinfo.is_virtual()      # it must be a non-virtual
                if self.optimizer.is_virtual(op.getarg(2)):
                    pendingfields.append(op)
                else:
                    cf.force_lazy_setfield(self, descr)                    
        return pendingfields

    def optimize_GETFIELD_GC_I(self, op):
        structinfo = self.ensure_ptr_info_arg0(op)
        cf = self.field_cache(op.getdescr())
        field = cf.getfield_from_cache(self, structinfo, op.getdescr())
        if field is not None:
            self.make_equal_to(op, field)
            return
        # default case: produce the operation
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
        # then remember the result of reading the field
        structinfo.setfield(op.getdescr(), op.getarg(0), op, self, cf)
    optimize_GETFIELD_GC_R = optimize_GETFIELD_GC_I
    optimize_GETFIELD_GC_F = optimize_GETFIELD_GC_I

    def optimize_GETFIELD_GC_PURE_I(self, op):
        structinfo = self.ensure_ptr_info_arg0(op)
        cf = self.field_cache(op.getdescr())
        field = cf.getfield_from_cache(self, structinfo, op.getdescr())
        if field is not None:
            self.make_equal_to(op, field)
            return
        # default case: produce the operation
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
    optimize_GETFIELD_GC_PURE_R = optimize_GETFIELD_GC_PURE_I
    optimize_GETFIELD_GC_PURE_F = optimize_GETFIELD_GC_PURE_I

    def optimize_SETFIELD_GC(self, op):
        self.setfield(op)
        #opnum = OpHelpers.getfield_pure_for_descr(op.getdescr())
        #if self.has_pure_result(opnum, [op.getarg(0)],
        #                        op.getdescr()):
        #    os.write(2, '[bogus _immutable_field_ declaration: %s]\n' %
        #             (op.getdescr().repr_of_descr()))
        #    raise BogusImmutableField
        #

    def setfield(self, op):
        cf = self.field_cache(op.getdescr())
        cf.do_setfield(self, op)

    def optimize_GETARRAYITEM_GC_I(self, op):
        arrayinfo = self.ensure_ptr_info_arg0(op)
        indexb = self.getintbound(op.getarg(1))
        cf = None
        if indexb.is_constant():
            index = indexb.getint()
            arrayinfo.getlenbound(None).make_gt_const(index)
            # use the cache on (arraydescr, index), which is a constant
            cf = self.arrayitem_cache(op.getdescr(), index)
            field = cf.getfield_from_cache(self, arrayinfo, op.getdescr())
            if field is not None:
                self.make_equal_to(op, field)
                return
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(),
                                         self.getintbound(op.getarg(1)))
        # default case: produce the operation
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)
        # the remember the result of reading the array item
        if cf is not None:
            arrayinfo.setitem(op.getdescr(), indexb.getint(),
                              self.get_box_replacement(op.getarg(0)),
                              self.get_box_replacement(op), cf,
                              self)
    optimize_GETARRAYITEM_GC_R = optimize_GETARRAYITEM_GC_I
    optimize_GETARRAYITEM_GC_F = optimize_GETARRAYITEM_GC_I

    def optimize_GETARRAYITEM_GC_PURE_I(self, op):
        arrayinfo = self.ensure_ptr_info_arg0(op)
        indexb = self.getintbound(op.getarg(1))
        cf = None
        if indexb.is_constant():
            index = indexb.getint()
            arrayinfo.getlenbound(None).make_gt_const(index)
            # use the cache on (arraydescr, index), which is a constant
            cf = self.arrayitem_cache(op.getdescr(), index)
            fieldvalue = cf.getfield_from_cache(self, arrayinfo, op.getdescr())
            if fieldvalue is not None:
                self.make_equal_to(op, fieldvalue)
                return
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(), self.getintbound(op.getarg(1)))
        # default case: produce the operation
        self.make_nonnull(op.getarg(0))
        self.emit_operation(op)

    optimize_GETARRAYITEM_GC_PURE_R = optimize_GETARRAYITEM_GC_PURE_I
    optimize_GETARRAYITEM_GC_PURE_F = optimize_GETARRAYITEM_GC_PURE_I

    def optimize_SETARRAYITEM_GC(self, op):
        #opnum = OpHelpers.getarrayitem_pure_for_descr(op.getdescr())
        #if self.has_pure_result(opnum, [op.getarg(0), op.getarg(1)],
        #                        op.getdescr()):
        #    os.write(2, '[bogus immutable array declaration: %s]\n' %
        #             (op.getdescr().repr_of_descr()))
        #    raise BogusImmutableField
        #
        indexb = self.getintbound(op.getarg(1))
        if indexb.is_constant():
            arrayinfo = self.ensure_ptr_info_arg0(op)
            # arraybound
            arrayinfo.getlenbound(None).make_gt_const(indexb.getint())
            cf = self.arrayitem_cache(op.getdescr(), indexb.getint())
            cf.do_setfield(self, op)
        else:
            # variable index, so make sure the lazy setarrayitems are done
            self.force_lazy_setarrayitem(op.getdescr(), indexb, can_cache=False)
            # and then emit the operation
            self.emit_operation(op)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # Pattern: QUASIIMMUT_FIELD(s, descr=QuasiImmutDescr)
        #          x = GETFIELD_GC_PURE(s, descr='inst_x')
        # If 's' is a constant (after optimizations) we rely on the rest of the
        # optimizations to constant-fold the following getfield_gc_pure.
        # in addition, we record the dependency here to make invalidation work
        # correctly.
        # NB: emitting the GETFIELD_GC_PURE is only safe because the
        # QUASIIMMUT_FIELD is also emitted to make sure the dependency is
        # registered.
        structvalue = self.ensure_ptr_info_arg0(op)
        if not structvalue.is_constant():
            self._remove_guard_not_invalidated = True
            return    # not a constant at all; ignore QUASIIMMUT_FIELD
        #
        from rpython.jit.metainterp.quasiimmut import QuasiImmutDescr
        qmutdescr = op.getdescr()
        assert isinstance(qmutdescr, QuasiImmutDescr)
        # check that the value is still correct; it could have changed
        # already between the tracing and now.  In this case, we mark the loop
        # as invalid
        if not qmutdescr.is_still_valid_for(
                self.get_box_replacement(op.getarg(0))):
            raise InvalidLoop('quasi immutable field changed during tracing')
        # record as an out-of-line guard
        if self.optimizer.quasi_immutable_deps is None:
            self.optimizer.quasi_immutable_deps = {}
        self.optimizer.quasi_immutable_deps[qmutdescr.qmut] = None
        self._remove_guard_not_invalidated = False

    def optimize_GUARD_NOT_INVALIDATED(self, op):
        if self._remove_guard_not_invalidated:
            return
        if self._seen_guard_not_invalidated:
            return
        self._seen_guard_not_invalidated = True
        self.emit_operation(op)


dispatch_opt = make_dispatcher_method(OptHeap, 'optimize_',
        default=OptHeap.emit_operation)
OptHeap.propagate_forward = dispatch_opt
