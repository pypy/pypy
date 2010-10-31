from pypy.jit.metainterp.optimizeutil import _findall
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import we_are_translated

from pypy.jit.metainterp.optimizeopt.optimizer import Optimization

class CachedArrayItems(object):
    def __init__(self):
        self.fixed_index_items = {}
        self.var_index_item = None
        self.var_index_indexvalue = None


class OptHeap(Optimization):
    """Cache repeated heap accesses"""
    
    def __init__(self):
        # cached fields:  {descr: {OptValue_instance: OptValue_fieldvalue}}
        self.cached_fields = {}
        # cached array items:  {descr: CachedArrayItems}
        self.cached_arrayitems = {}
        # lazily written setfields (at most one per descr):  {descr: op}
        self.lazy_setfields = {}
        self.lazy_setfields_descrs = []     # keys (at least) of previous dict

    def clean_caches(self):
        self.cached_fields.clear()
        self.cached_arrayitems.clear()

    def cache_field_value(self, descr, value, fieldvalue, write=False):
        if write:
            # when seeing a setfield, we have to clear the cache for the same
            # field on any other structure, just in case they are aliasing
            # each other
            d = self.cached_fields[descr] = {}
        else:
            d = self.cached_fields.setdefault(descr, {})
        d[value] = fieldvalue

    def read_cached_field(self, descr, value):
        # XXX self.cached_fields and self.lazy_setfields should probably
        # be merged somehow
        d = self.cached_fields.get(descr, None)
        if d is None:
            op = self.lazy_setfields.get(descr, None)
            if op is None:
                return None
            return self.getvalue(op.getarg(1))
        return d.get(value, None)

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
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETFIELD_RAW or
            opnum == rop.SETARRAYITEM_GC or
            opnum == rop.SETARRAYITEM_RAW or
            opnum == rop.DEBUG_MERGE_POINT):
            return
        assert opnum != rop.CALL_PURE
        if (opnum == rop.CALL or
            opnum == rop.CALL_MAY_FORCE or
            opnum == rop.CALL_ASSEMBLER):
            if opnum == rop.CALL_ASSEMBLER:
                effectinfo = None
            else:
                effectinfo = op.getdescr().get_extra_info()
            if effectinfo is not None:
                # XXX we can get the wrong complexity here, if the lists
                # XXX stored on effectinfo are large
                for fielddescr in effectinfo.readonly_descrs_fields:
                    self.force_lazy_setfield(fielddescr)
                for fielddescr in effectinfo.write_descrs_fields:
                    self.force_lazy_setfield(fielddescr)
                    try:
                        del self.cached_fields[fielddescr]
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
        elif op.is_final() or (not we_are_translated() and
                               op.getopnum() < 0):   # escape() operations
            self.force_all_lazy_setfields()
        self.clean_caches()


    def force_at_end_of_preamble(self):
        self.force_all_lazy_setfields()
        
    def force_lazy_setfield(self, descr, before_guard=False):
        try:
            op = self.lazy_setfields[descr]
        except KeyError:
            return
        del self.lazy_setfields[descr]
        ###self.optimizer._emit_operation(op)
        self.next_optimization.propagate_forward(op)
        #
        # hackish: reverse the order of the last two operations if it makes
        # sense to avoid a situation like "int_eq/setfield_gc/guard_true",
        # which the backend (at least the x86 backend) does not handle well.
        newoperations = self.optimizer.newoperations
        if before_guard and len(newoperations) >= 2:
            lastop = newoperations[-1]
            prevop = newoperations[-2]
            # - is_comparison() for cases like "int_eq/setfield_gc/guard_true"
            # - CALL_MAY_FORCE: "call_may_force/setfield_gc/guard_not_forced"
            # - is_ovf(): "int_add_ovf/setfield_gc/guard_no_overflow"
            opnum = prevop.getopnum()
            lastop_args = lastop.getarglist()
            if ((prevop.is_comparison() or opnum == rop.CALL_MAY_FORCE
                 or prevop.is_ovf())
                and prevop.result not in lastop_args):
                newoperations[-2] = lastop
                newoperations[-1] = prevop

    def force_all_lazy_setfields(self):
        if len(self.lazy_setfields_descrs) > 0:
            for descr in self.lazy_setfields_descrs:
                self.force_lazy_setfield(descr)
            del self.lazy_setfields_descrs[:]

    def force_lazy_setfields_for_guard(self):
        pendingfields = []
        for descr in self.lazy_setfields_descrs:
            try:
                op = self.lazy_setfields[descr]
            except KeyError:
                continue
            # the only really interesting case that we need to handle in the
            # guards' resume data is that of a virtual object that is stored
            # into a field of a non-virtual object.
            value = self.getvalue(op.getarg(0))
            assert not value.is_virtual()      # it must be a non-virtual
            fieldvalue = self.getvalue(op.getarg(1))
            if fieldvalue.is_virtual():
                # this is the case that we leave to resume.py
                pendingfields.append((descr, value.box,
                                      fieldvalue.get_key_box()))
            else:
                self.force_lazy_setfield(descr, before_guard=True)
        return pendingfields

    def force_lazy_setfield_if_necessary(self, op, value, write=False):
        try:
            op1 = self.lazy_setfields[op.getdescr()]
        except KeyError:
            if write:
                self.lazy_setfields_descrs.append(op.getdescr())
        else:
            if self.getvalue(op1.getarg(0)) is not value:
                self.force_lazy_setfield(op.getdescr())

    def optimize_GETFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))
        self.force_lazy_setfield_if_necessary(op, value)
        # check if the field was read from another getfield_gc just before
        # or has been written to recently
        fieldvalue = self.read_cached_field(op.getdescr(), value)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        # default case: produce the operation
        value.ensure_nonnull()
        ###self.optimizer.optimize_default(op)
        self.emit_operation(op) # FIXME: These might need constant propagation?
        # then remember the result of reading the field
        fieldvalue = self.getvalue(op.result)
        self.cache_field_value(op.getdescr(), value, fieldvalue)

    def optimize_SETFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))
        fieldvalue = self.getvalue(op.getarg(1))
        self.force_lazy_setfield_if_necessary(op, value, write=True)
        self.lazy_setfields[op.getdescr()] = op
        # remember the result of future reads of the field
        self.cache_field_value(op.getdescr(), value, fieldvalue, write=True)

    def optimize_GETARRAYITEM_GC(self, op):
        value = self.getvalue(op.getarg(0))
        indexvalue = self.getvalue(op.getarg(1))
        fieldvalue = self.read_cached_arrayitem(op.getdescr(), value, indexvalue)
        if fieldvalue is not None:
            self.make_equal_to(op.result, fieldvalue)
            return
        ###self.optimizer.optimize_default(op)
        self.emit_operation(op) # FIXME: These might need constant propagation?
        fieldvalue = self.getvalue(op.result)
        self.cache_arrayitem_value(op.getdescr(), value, indexvalue, fieldvalue)

    def optimize_SETARRAYITEM_GC(self, op):
        self.emit_operation(op)
        value = self.getvalue(op.getarg(0))
        fieldvalue = self.getvalue(op.getarg(2))
        indexvalue = self.getvalue(op.getarg(1))
        self.cache_arrayitem_value(op.getdescr(), value, indexvalue, fieldvalue,
                                   write=True)

    def propagate_forward(self, op):
        opnum = op.getopnum()
        for value, func in optimize_ops:
            if opnum == value:
                func(self, op)
                break
        else:
            self.emit_operation(op)

optimize_ops = _findall(OptHeap, 'optimize_')
