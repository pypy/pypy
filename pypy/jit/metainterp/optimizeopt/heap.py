import os
from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.jitexc import JitException
from pypy.jit.metainterp.optimizeopt.optimizer import Optimization


class CachedField(object):
    def __init__(self):
        # Cache information for a field descr.  It can be in one
        # of two states:
        #
        #   1. 'cached_fields' is a dict mapping OptValues of structs
        #      to OptValues of fields.  All fields on-heap are
        #      synchronized with the values stored in the cache.
        #
        #   2. we just did one setfield, which is delayed (and thus
        #      not synchronized).  'lazy_setfield' is the delayed
        #      ResOperation.  In this state, 'cached_fields' contains
        #      out-of-date information.  More precisely, the field
        #      value pending in the ResOperation is *not* visible in
        #      'cached_fields'.
        #
        self._cached_fields = {}
        self._lazy_setfield = None
        self._lazy_setfield_registered = False

    def do_setfield(self, optheap, op):
        # Update the state with the SETFIELD_GC operation 'op'.
        structvalue = optheap.getvalue(op.getarg(0))
        fieldvalue  = optheap.getvalue(op.getarg(1))
        if self.possible_aliasing(optheap, structvalue):
            self.force_lazy_setfield(optheap)
            assert not self.possible_aliasing(optheap, structvalue)
        cached_fieldvalue = self._cached_fields.get(structvalue, None)
        if cached_fieldvalue is not fieldvalue:
            # common case: store the 'op' as lazy_setfield, and register
            # myself in the optheap's _lazy_setfields list
            self._lazy_setfield = op
            if not self._lazy_setfield_registered:
                optheap._lazy_setfields.append(self)
                self._lazy_setfield_registered = True
        else:
            # this is the case where the pending setfield ends up
            # storing precisely the value that is already there,
            # as proved by 'cached_fields'.  In this case, we don't
            # need any _lazy_setfield: the heap value is already right.
            # Note that this may reset to None a non-None lazy_setfield,
            # cancelling its previous effects with no side effect.
            self._lazy_setfield = None

    def possible_aliasing(self, optheap, structvalue):
        # If lazy_setfield is set and contains a setfield on a different
        # structvalue, then we are annoyed, because it may point to either
        # the same or a different structure at runtime.
        return (self._lazy_setfield is not None
                and (optheap.getvalue(self._lazy_setfield.getarg(0))
                     is not structvalue))

    def getfield_from_cache(self, optheap, structvalue):
        # Returns the up-to-date field's value, or None if not cached.
        if self.possible_aliasing(optheap, structvalue):
            self.force_lazy_setfield(optheap)
        if self._lazy_setfield is not None:
            op = self._lazy_setfield
            assert optheap.getvalue(op.getarg(0)) is structvalue
            return optheap.getvalue(op.getarg(1))
        else:
            return self._cached_fields.get(structvalue, None)

    def remember_field_value(self, structvalue, fieldvalue):
        assert self._lazy_setfield is None
        self._cached_fields[structvalue] = fieldvalue

    def force_lazy_setfield(self, optheap):
        op = self._lazy_setfield
        if op is not None:
            # This is the way _lazy_setfield is usually reset to None.
            # Now we clear _cached_fields, because actually doing the
            # setfield might impact any of the stored result (because of
            # possible aliasing).
            self._cached_fields.clear()
            self._lazy_setfield = None
            optheap.next_optimization.propagate_forward(op)
            # Once it is done, we can put at least one piece of information
            # back in the cache: the value of this particular structure's
            # field.
            structvalue = optheap.getvalue(op.getarg(0))
            fieldvalue  = optheap.getvalue(op.getarg(1))
            self.remember_field_value(structvalue, fieldvalue)

    def get_reconstructed(self, optimizer, valuemap):
        assert self._lazy_setfield is None
        cf = CachedField()
        for structvalue, fieldvalue in self._cached_fields.iteritems():
            structvalue2 = structvalue.get_reconstructed(optimizer, valuemap)
            fieldvalue2  = fieldvalue .get_reconstructed(optimizer, valuemap)
            cf._cached_fields[structvalue2] = fieldvalue2
        return cf


class CachedArrayItems(object):
    def __init__(self):
        self.fixed_index_items = {}
        self.var_index_item = None
        self.var_index_indexvalue = None

class BogusPureField(JitException):
    pass


class OptHeap(Optimization):
    """Cache repeated heap accesses"""
    
    def __init__(self):
        # cached fields:  {descr: CachedField}
        self.cached_fields = {}
        self._lazy_setfields = []
        # cached array items:  {descr: CachedArrayItems}
        self.cached_arrayitems = {}
        self._remove_guard_not_invalidated = False
        self._seen_guard_not_invalidated = False

    def reconstruct_for_next_iteration(self, optimizer, valuemap):
        new = OptHeap()

        if True:
            self.force_all_lazy_setfields()
        else:
            assert 0   # was: new.lazy_setfields = self.lazy_setfields
        
        for descr, d in self.cached_fields.items():
            new.cached_fields[descr] = d.get_reconstructed(optimizer, valuemap)

        new.cached_arrayitems = {}
        for descr, d in self.cached_arrayitems.items():
            newd = {}
            new.cached_arrayitems[descr] = newd
            for value, cache in d.items():
                newcache = CachedArrayItems()
                newd[value.get_reconstructed(optimizer, valuemap)] = newcache
                if cache.var_index_item:
                    newcache.var_index_item = \
                          cache.var_index_item.get_reconstructed(optimizer, valuemap)
                if cache.var_index_indexvalue:
                    newcache.var_index_indexvalue = \
                          cache.var_index_indexvalue.get_reconstructed(optimizer, valuemap)
                for index, fieldvalue in cache.fixed_index_items.items():
                    newcache.fixed_index_items[index] = \
                           fieldvalue.get_reconstructed(optimizer, valuemap)

        return new

    def clean_caches(self):
        del self._lazy_setfields[:]
        self.cached_fields.clear()
        self.cached_arrayitems.clear()

    def field_cache(self, descr):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            cf = self.cached_fields[descr] = CachedField()
        return cf

    def cache_arrayitem_value(self, descr, value, indexvalue, fieldvalue, write=False):
        d = self.cached_arrayitems.get(descr, None)
        if d is None:
            d = self.cached_arrayitems[descr] = {}
        cache = d.get(value, None)
        if cache is None:
            cache = d[value] = CachedArrayItems()
        indexbox = self.get_constant_box(indexvalue.box)
        if indexbox is not None:
            index = indexbox.getint()
            if write:
                for value, othercache in d.iteritems():
                    # fixed index, clean the variable index cache, in case the
                    # index is the same
                    othercache.var_index_indexvalue = None
                    othercache.var_index_item = None
                    try:
                        del othercache.fixed_index_items[index]
                    except KeyError:
                        pass
            cache.fixed_index_items[index] = fieldvalue
        else:
            if write:
                for value, othercache in d.iteritems():
                    # variable index, clear all caches for this descr
                    othercache.var_index_indexvalue = None
                    othercache.var_index_item = None
                    othercache.fixed_index_items.clear()
            cache.var_index_indexvalue = indexvalue
            cache.var_index_item = fieldvalue

    def read_cached_arrayitem(self, descr, value, indexvalue):
        d = self.cached_arrayitems.get(descr, None)
        if d is None:
            return None
        cache = d.get(value, None)
        if cache is None:
            return None
        indexbox = self.get_constant_box(indexvalue.box)
        if indexbox is not None:
            return cache.fixed_index_items.get(indexbox.getint(), None)
        elif cache.var_index_indexvalue is indexvalue:
            return cache.var_index_item
        return None

    def emit_operation(self, op):
        self.emitting_operation(op)
        self.next_optimization.propagate_forward(op)

    def emitting_operation(self, op):
        if op.has_no_side_effect():
            return
        if op.is_ovf():
            return
        if op.is_guard():
            self.optimizer.pendingfields = self.force_lazy_setfields_for_guard()
            return
        opnum = op.getopnum()
        if (opnum == rop.SETFIELD_GC or        # handled specially
            opnum == rop.SETFIELD_RAW or       # no effect on GC struct/array
            opnum == rop.SETARRAYITEM_GC or    # handled specially
            opnum == rop.SETARRAYITEM_RAW or   # no effect on GC struct
            opnum == rop.STRSETITEM or         # no effect on GC struct/array
            opnum == rop.UNICODESETITEM or     # no effect on GC struct/array
            opnum == rop.DEBUG_MERGE_POINT or  # no effect whatsoever
            opnum == rop.COPYSTRCONTENT or     # no effect on GC struct/array
            opnum == rop.COPYUNICODECONTENT):  # no effect on GC struct/array
            return
        assert opnum != rop.CALL_PURE
        if (opnum == rop.CALL or
            opnum == rop.CALL_MAY_FORCE or
            opnum == rop.CALL_ASSEMBLER):
            if opnum == rop.CALL_ASSEMBLER:
                effectinfo = None
            else:
                effectinfo = op.getdescr().get_extra_info()
            if (effectinfo is None or effectinfo.extraeffect >=
                effectinfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE):
                self._seen_guard_not_invalidated = False
            if effectinfo is not None:
                # XXX we can get the wrong complexity here, if the lists
                # XXX stored on effectinfo are large
                for fielddescr in effectinfo.readonly_descrs_fields:
                    self.force_lazy_setfield(fielddescr)
                for fielddescr in effectinfo.write_descrs_fields:
                    self.force_lazy_setfield(fielddescr)
                    try:
                        cf = self.cached_fields[fielddescr]
                        cf._cached_fields.clear()
                    except KeyError:
                        pass
                for arraydescr in effectinfo.write_descrs_arrays:
                    try:
                        del self.cached_arrayitems[arraydescr]
                    except KeyError:
                        pass
                if effectinfo.check_forces_virtual_or_virtualizable():
                    vrefinfo = self.optimizer.metainterp_sd.virtualref_info
                    self.force_lazy_setfield(vrefinfo.descr_forced)
                    # ^^^ we only need to force this field; the other fields
                    # of virtualref_info and virtualizable_info are not gcptrs.
                return
        self.force_all_lazy_setfields()
        self.clean_caches()


    def turned_constant(self, value):
        assert value.is_constant()
        newvalue = self.getvalue(value.box)
        if value is not newvalue:
            for cf in self.cached_fields.itervalues():
                if value in cf._cached_fields:
                    cf._cached_fields[newvalue] = cf._cached_fields[value]

    def force_lazy_setfield(self, descr):
        try:
            cf = self.cached_fields[descr]
        except KeyError:
            return
        cf.force_lazy_setfield(self)

    def fixup_guard_situation(self):
        # hackish: reverse the order of the last two operations if it makes
        # sense to avoid a situation like "int_eq/setfield_gc/guard_true",
        # which the backend (at least the x86 backend) does not handle well.
        newoperations = self.optimizer.newoperations
        if len(newoperations) < 2:
            return
        lastop = newoperations[-1]
        if (lastop.getopnum() != rop.SETFIELD_GC and
            lastop.getopnum() != rop.SETARRAYITEM_GC):
            return
        # - is_comparison() for cases like "int_eq/setfield_gc/guard_true"
        # - CALL_MAY_FORCE: "call_may_force/setfield_gc/guard_not_forced"
        # - is_ovf(): "int_add_ovf/setfield_gc/guard_no_overflow"
        prevop = newoperations[-2]
        opnum = prevop.getopnum()
        if not (prevop.is_comparison() or opnum == rop.CALL_MAY_FORCE
                or prevop.is_ovf()):
            return
        if prevop.result in lastop.getarglist():
            return
        newoperations[-2] = lastop
        newoperations[-1] = prevop

    def force_all_lazy_setfields(self):
        for cf in self._lazy_setfields:
            if not we_are_translated():
                assert cf in self.cached_fields.values()
            cf.force_lazy_setfield(self)

    def force_lazy_setfields_for_guard(self):
        pendingfields = []
        for cf in self._lazy_setfields:
            if not we_are_translated():
                assert cf in self.cached_fields.values()
            op = cf._lazy_setfield
            if op is None:
                continue
            # the only really interesting case that we need to handle in the
            # guards' resume data is that of a virtual object that is stored
            # into a field of a non-virtual object.
            value = self.getvalue(op.getarg(0))
            assert not value.is_virtual()      # it must be a non-virtual
            fieldvalue = self.getvalue(op.getarg(1))
            if fieldvalue.is_virtual():
                # this is the case that we leave to resume.py
                pendingfields.append((op.getdescr(), value.box,
                                      fieldvalue.get_key_box()))
            else:
                cf.force_lazy_setfield(self)
                self.fixup_guard_situation()
        return pendingfields

    def optimize_GETFIELD_GC(self, op):
        structvalue = self.getvalue(op.getarg(0))
        cf = self.field_cache(op.getdescr())
        fieldvalue = cf.getfield_from_cache(self, structvalue)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        # default case: produce the operation
        structvalue.ensure_nonnull()
        ###self.optimizer.optimize_default(op)
        self.emit_operation(op)
        # then remember the result of reading the field
        fieldvalue = self.getvalue(op.result)
        cf.remember_field_value(structvalue, fieldvalue)

    def optimize_SETFIELD_GC(self, op):
        if self.has_pure_result(rop.GETFIELD_GC_PURE, [op.getarg(0)],
                                op.getdescr()):
            os.write(2, '[bogus _immutable_field_ declaration: %s]\n' %
                     (op.getdescr().repr_of_descr()))
            raise BogusPureField
        #
        cf = self.field_cache(op.getdescr())
        cf.do_setfield(self, op)

    def optimize_GETARRAYITEM_GC(self, op):
        value = self.getvalue(op.getarg(0))
        indexvalue = self.getvalue(op.getarg(1))
        fieldvalue = self.read_cached_arrayitem(op.getdescr(), value, indexvalue)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        ###self.optimizer.optimize_default(op)
        self.emit_operation(op)
        fieldvalue = self.getvalue(op.result)
        self.cache_arrayitem_value(op.getdescr(), value, indexvalue, fieldvalue)

    def optimize_SETARRAYITEM_GC(self, op):
        self.emit_operation(op)
        value = self.getvalue(op.getarg(0))
        fieldvalue = self.getvalue(op.getarg(2))
        indexvalue = self.getvalue(op.getarg(1))
        self.cache_arrayitem_value(op.getdescr(), value, indexvalue, fieldvalue,
                                   write=True)

    def optimize_QUASIIMMUT_FIELD(self, op):
        # Pattern: QUASIIMMUT_FIELD(s, descr=QuasiImmutDescr)
        #          x = GETFIELD_GC(s, descr='inst_x')
        # If 's' is a constant (after optimizations), then we make 's.inst_x'
        # a constant too, and we rely on the rest of the optimizations to
        # constant-fold the following getfield_gc.
        structvalue = self.getvalue(op.getarg(0))
        if not structvalue.is_constant():
            self._remove_guard_not_invalidated = True
            return    # not a constant at all; ignore QUASIIMMUT_FIELD
        #
        from pypy.jit.metainterp.quasiimmut import QuasiImmutDescr
        qmutdescr = op.getdescr()
        assert isinstance(qmutdescr, QuasiImmutDescr)
        # check that the value is still correct; it could have changed
        # already between the tracing and now.  In this case, we are
        # simply ignoring the QUASIIMMUT_FIELD hint and compiling it
        # as a regular getfield.
        if not qmutdescr.is_still_valid():
            self._remove_guard_not_invalidated = True
            return
        # record as an out-of-line guard
        if self.optimizer.quasi_immutable_deps is None:
            self.optimizer.quasi_immutable_deps = {}
        self.optimizer.quasi_immutable_deps[qmutdescr.qmut] = None
        # perform the replacement in the list of operations
        fieldvalue = self.getvalue(qmutdescr.constantfieldbox)
        cf = self.field_cache(qmutdescr.fielddescr)
        cf.remember_field_value(structvalue, fieldvalue)
        self._remove_guard_not_invalidated = False

    def optimize_GUARD_NOT_INVALIDATED(self, op):
        if self._remove_guard_not_invalidated:
            return
        self._remove_guard_not_invalidated = False        # XXX ???
        if self._seen_guard_not_invalidated:
            return
        self._seen_guard_not_invalidated = True
        self.emit_operation(op)

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptHeap, 'optimize_')
