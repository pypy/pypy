from pypy.jit.codewriter.heaptracker import vtable2descr
from pypy.jit.metainterp.executor import execute
from pypy.jit.metainterp.history import Const, ConstInt, BoxInt
from pypy.jit.metainterp.optimizeopt import optimizer
from pypy.jit.metainterp.optimizeopt.util import (make_dispatcher_method,
    descrlist_dict, sort_descrs)
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import we_are_translated
from pypy.jit.metainterp.optimizeopt.optimizer import OptValue


class AbstractVirtualValue(optimizer.OptValue):
    _attrs_ = ('keybox', 'source_op', '_cached_vinfo')
    box = None
    level = optimizer.LEVEL_NONNULL
    _cached_vinfo = None

    def __init__(self, keybox, source_op=None):
        self.keybox = keybox   # only used as a key in dictionaries
        self.source_op = source_op  # the NEW_WITH_VTABLE/NEW_ARRAY operation
                                    # that builds this box

    def is_forced_virtual(self):
        return self.box is not None

    def get_key_box(self):
        if self.box is None:
            return self.keybox
        return self.box

    def force_box(self, optforce):
        if self.box is None:
            optforce.forget_numberings(self.keybox)
            self._really_force(optforce)
        return self.box

    def force_at_end_of_preamble(self, already_forced, optforce):
        value = already_forced.get(self, None)
        if value:
            return value
        return OptValue(self.force_box(optforce))

    def make_virtual_info(self, modifier, fieldnums):
        if fieldnums is None:
            return self._make_virtual(modifier)
        vinfo = self._cached_vinfo
        if vinfo is not None and vinfo.equals(fieldnums):
            return vinfo
        vinfo = self._make_virtual(modifier)
        vinfo.set_content(fieldnums)
        self._cached_vinfo = vinfo
        return vinfo

    def _make_virtual(self, modifier):
        raise NotImplementedError("abstract base")

    def _really_force(self, optforce):
        raise NotImplementedError("abstract base")

    def import_from(self, other, optimizer):
        raise NotImplementedError("should not be called at this level")

def get_fielddescrlist_cache(cpu):
    if not hasattr(cpu, '_optimizeopt_fielddescrlist_cache'):
        result = descrlist_dict()
        cpu._optimizeopt_fielddescrlist_cache = result
        return result
    return cpu._optimizeopt_fielddescrlist_cache
get_fielddescrlist_cache._annspecialcase_ = "specialize:memo"

class AbstractVirtualStructValue(AbstractVirtualValue):
    _attrs_ = ('_fields', 'cpu', '_cached_sorted_fields')

    def __init__(self, cpu, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, keybox, source_op)
        self.cpu = cpu
        self._fields = {}
        self._cached_sorted_fields = None

    def getfield(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        assert isinstance(fieldvalue, optimizer.OptValue)
        self._fields[ofs] = fieldvalue

    def _get_descr(self):
        raise NotImplementedError

    def _is_immutable_and_filled_with_constants(self, optforce):
        count = self._get_descr().count_fields_if_immutable()
        if count != len(self._fields):    # always the case if count == -1
            return False
        for value in self._fields.itervalues():
            subbox = value.force_box(optforce)
            if not isinstance(subbox, Const):
                return False
        return True

    def force_at_end_of_preamble(self, already_forced, optforce):
        if self in already_forced:
            return self
        already_forced[self] = self
        if self._fields:
            for ofs in self._fields.keys():
                self._fields[ofs] = self._fields[ofs].force_at_end_of_preamble(already_forced, optforce)
        return self

    def _really_force(self, optforce):
        op = self.source_op
        assert op is not None
        # ^^^ This case should not occur any more (see test_bug_3).
        #
        if not we_are_translated():
            op.name = 'FORCE ' + self.source_op.name

        if self._is_immutable_and_filled_with_constants(optforce):
            box = optforce.optimizer.constant_fold(op)
            self.make_constant(box)
            for ofs, value in self._fields.iteritems():
                subbox = value.force_box(optforce)
                assert isinstance(subbox, Const)
                execute(optforce.optimizer.cpu, None, rop.SETFIELD_GC,
                        ofs, box, subbox)
            # keep self._fields, because it's all immutable anyway
        else:
            optforce.emit_operation(op)
            self.box = box = op.result
            #
            iteritems = self._fields.iteritems()
            if not we_are_translated(): #random order is fine, except for tests
                iteritems = list(iteritems)
                iteritems.sort(key = lambda (x,y): x.sort_key())
            for ofs, value in iteritems:
                if value.is_null():
                    continue
                subbox = value.force_box(optforce)
                op = ResOperation(rop.SETFIELD_GC, [box, subbox], None,
                                  descr=ofs)

                optforce.emit_operation(op)

    def _get_field_descr_list(self):
        _cached_sorted_fields = self._cached_sorted_fields
        if self._fields is None:
            nfields = 0
        else:
            nfields = len(self._fields)
        if (_cached_sorted_fields is not None and
            nfields == len(_cached_sorted_fields)):
            lst = self._cached_sorted_fields
        else:
            if self._fields is None:
                lst = []
            else:
                lst = self._fields.keys()
            sort_descrs(lst)
            cache = get_fielddescrlist_cache(self.cpu)
            result = cache.get(lst, None)
            if result is None:
                cache[lst] = lst
            else:
                lst = result
            # store on self, to not have to repeatedly get it from the global
            # cache, which involves sorting
            self._cached_sorted_fields = lst
        return lst

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            # checks for recursion: it is False unless
            # we have already seen the very same keybox
            lst = self._get_field_descr_list()
            fieldboxes = [self._fields[ofs].get_key_box() for ofs in lst]
            modifier.register_virtual_fields(self.keybox, fieldboxes)
            for ofs in lst:
                fieldvalue = self._fields[ofs]
                fieldvalue.get_args_for_fail(modifier)

class VirtualValue(AbstractVirtualStructValue):
    level = optimizer.LEVEL_KNOWNCLASS

    def __init__(self, cpu, known_class, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, cpu, keybox, source_op)
        assert isinstance(known_class, Const)
        self.known_class = known_class

    def _make_virtual(self, modifier):
        fielddescrs = self._get_field_descr_list()
        return modifier.make_virtual(self.known_class, fielddescrs)

    def _get_descr(self):
        return vtable2descr(self.cpu, self.known_class.getint())

    def __repr__(self):
        cls_name = self.known_class.value.adr.ptr._obj._TYPE._name
        if self._fields is None:
            return '<VirtualValue FORCED cls=%s>' % (cls_name,)
        field_names = [field.name for field in self._fields]
        return "<VirtualValue cls=%s fields=%s>" % (cls_name, field_names)

class VStructValue(AbstractVirtualStructValue):

    def __init__(self, cpu, structdescr, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, cpu, keybox, source_op)
        self.structdescr = structdescr

    def _make_virtual(self, modifier):
        fielddescrs = self._get_field_descr_list()
        return modifier.make_vstruct(self.structdescr, fielddescrs)

    def _get_descr(self):
        return self.structdescr


class VArrayValue(AbstractVirtualValue):

    def __init__(self, arraydescr, constvalue, size, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, keybox, source_op)
        self.arraydescr = arraydescr
        self.constvalue = constvalue
        self._items = [self.constvalue] * size

    def getlength(self):
        return len(self._items)

    def getitem(self, index):
        res = self._items[index]
        return res

    def setitem(self, index, itemvalue):
        assert isinstance(itemvalue, optimizer.OptValue)
        self._items[index] = itemvalue

    def force_at_end_of_preamble(self, already_forced, optforce):
        if self in already_forced:
            return self
        already_forced[self] = self
        for index in range(len(self._items)):
            self._items[index] = self._items[index].force_at_end_of_preamble(already_forced, optforce)
        return self

    def _really_force(self, optforce):
        assert self.source_op is not None
        if not we_are_translated():
            self.source_op.name = 'FORCE ' + self.source_op.name
        optforce.emit_operation(self.source_op)
        self.box = box = self.source_op.result
        for index in range(len(self._items)):
            subvalue = self._items[index]
            if subvalue is not self.constvalue:
                if subvalue.is_null():
                    continue
                subbox = subvalue.force_box(optforce)
                op = ResOperation(rop.SETARRAYITEM_GC,
                                  [box, ConstInt(index), subbox], None,
                                  descr=self.arraydescr)
                optforce.emit_operation(op)

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            # checks for recursion: it is False unless
            # we have already seen the very same keybox
            itemboxes = []
            for itemvalue in self._items:
                itemboxes.append(itemvalue.get_key_box())
            modifier.register_virtual_fields(self.keybox, itemboxes)
            for itemvalue in self._items:
                itemvalue.get_args_for_fail(modifier)

    def _make_virtual(self, modifier):
        return modifier.make_varray(self.arraydescr)

class VArrayStructValue(AbstractVirtualValue):
    def __init__(self, arraydescr, size, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, keybox, source_op)
        self.arraydescr = arraydescr
        self._items = [{} for _ in xrange(size)]

    def getlength(self):
        return len(self._items)

    def getinteriorfield(self, index, descr, default):
        return self._items[index].get(descr, default)

    def setinteriorfield(self, index, descr, itemvalue):
        assert isinstance(itemvalue, optimizer.OptValue)
        self._items[index][descr] = itemvalue

    def _really_force(self, optforce):
        raise NotImplementedError
        assert self.source_op is not None
        if not we_are_translated():
            self.source_op.name = 'FORCE ' + self.source_op.name
        optforce.emit_operation(self.source_op)
        self.box = box = self.source_op.result
        for index in range(len(self._items)):
            for descr, value in self._items[index].iteritems():
                subbox = value.force_box(optforce)
                op = ResOperation(rop.SETINTERIORFIELD_GC, [box, ConstInt(index), subbox], None, descr=descr)
                optforce.emit_operation(op)

    def force_at_end_of_preamble(self, already_forced, optforce):
        if self in already_forced:
            return self
        already_forced[self] = self
        for index in range(len(self._items)):
            for descr in self._items[index].keys():
                self._items[index][descr] = self._items[index][descr].force_at_end_of_preamble(already_forced, optforce)
        return self

    def _make_virtual(self, modifier):
        return modifier.make_varraystruct(self.arraydescr)


class OptVirtualize(optimizer.Optimization):
    "Virtualize objects until they escape."

    def new(self):
        return OptVirtualize()

    def make_virtual(self, known_class, box, source_op=None):
        vvalue = VirtualValue(self.optimizer.cpu, known_class, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_varray(self, arraydescr, size, box, source_op=None):
        if arraydescr.is_array_of_structs():
            vvalue = VArrayStructValue(arraydescr, size, box, source_op)
        else:
            constvalue = self.new_const_item(arraydescr)
            vvalue = VArrayValue(arraydescr, constvalue, size, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstruct(self, structdescr, box, source_op=None):
        vvalue = VStructValue(self.optimizer.cpu, structdescr, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def optimize_VIRTUAL_REF(self, op):
        indexbox = op.getarg(1)
        #
        # get some constants
        vrefinfo = self.optimizer.metainterp_sd.virtualref_info
        c_cls = vrefinfo.jit_virtual_ref_const_class
        descr_virtual_token = vrefinfo.descr_virtual_token
        #
        # Replace the VIRTUAL_REF operation with a virtual structure of type
        # 'jit_virtual_ref'.  The jit_virtual_ref structure may be forced soon,
        # but the point is that doing so does not force the original structure.
        op = ResOperation(rop.NEW_WITH_VTABLE, [c_cls], op.result)
        vrefvalue = self.make_virtual(c_cls, op.result, op)
        tokenbox = BoxInt()
        self.emit_operation(ResOperation(rop.FORCE_TOKEN, [], tokenbox))
        vrefvalue.setfield(descr_virtual_token, self.getvalue(tokenbox))

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
        if not self.optimizer.cpu.ts.CONST_NULL.same_constant(objbox):
            seo(ResOperation(rop.SETFIELD_GC, op.getarglist(), None,
                             descr = vrefinfo.descr_forced))

        # - set 'virtual_token' to TOKEN_NONE
        args = [op.getarg(0), ConstInt(vrefinfo.TOKEN_NONE)]
        seo(ResOperation(rop.SETFIELD_GC, args, None,
                         descr = vrefinfo.descr_virtual_token))
        # Note that in some cases the virtual in op.getarg(1) has been forced
        # already.  This is fine.  In that case, and *if* a residual
        # CALL_MAY_FORCE suddenly turns out to access it, then it will
        # trigger a ResumeGuardForcedDescr.handle_async_forcing() which
        # will work too (but just be a little pointless, as the structure
        # was already forced).

    def optimize_GETFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))
        # If this is an immutable field (as indicated by op.is_always_pure())
        # then it's safe to reuse the virtual's field, even if it has been
        # forced, because it should never be written to again.
        if value.is_forced_virtual() and op.is_always_pure():
            fieldvalue = value.getfield(op.getdescr(), None)
            if fieldvalue is not None:
                self.make_equal_to(op.result, fieldvalue)
                return
        if value.is_virtual():
            assert isinstance(value, AbstractVirtualValue)
            fieldvalue = value.getfield(op.getdescr(), None)
            if fieldvalue is None:
                fieldvalue = self.optimizer.new_const(op.getdescr())
            self.make_equal_to(op.result, fieldvalue)
        else:
            value.ensure_nonnull()
            self.emit_operation(op)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETFIELD_GC_PURE is_always_pure().
    optimize_GETFIELD_GC_PURE = optimize_GETFIELD_GC

    def optimize_SETFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))

        if value.is_virtual():
            fieldvalue = self.getvalue(op.getarg(1))
            value.setfield(op.getdescr(), fieldvalue)
        else:
            value.ensure_nonnull()
            self.emit_operation(op)

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.getarg(0), op.result, op)

    def optimize_NEW(self, op):
        self.make_vstruct(op.getdescr(), op.result, op)

    def optimize_NEW_ARRAY(self, op):
        sizebox = self.get_constant_box(op.getarg(0))
        if sizebox is not None:
            # if the original 'op' did not have a ConstInt as argument,
            # build a new one with the ConstInt argument
            if not isinstance(op.getarg(0), ConstInt):
                op = ResOperation(rop.NEW_ARRAY, [sizebox], op.result,
                                  descr=op.getdescr())
            self.make_varray(op.getdescr(), sizebox.getint(), op.result, op)
        else:
            self.getvalue(op.result).ensure_nonnull()
            self.emit_operation(op)

    def optimize_ARRAYLEN_GC(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            self.make_constant_int(op.result, value.getlength())
        else:
            value.ensure_nonnull()
            ###self.optimize_default(op)
            self.emit_operation(op)

    def optimize_GETARRAYITEM_GC(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                itemvalue = value.getitem(indexbox.getint())
                self.make_equal_to(op.result, itemvalue)
                return
        value.ensure_nonnull()
        self.emit_operation(op)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETARRAYITEM_GC_PURE is_always_pure().
    optimize_GETARRAYITEM_GC_PURE = optimize_GETARRAYITEM_GC

    def optimize_SETARRAYITEM_GC(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                value.setitem(indexbox.getint(), self.getvalue(op.getarg(2)))
                return
        value.ensure_nonnull()
        self.emit_operation(op)

    def optimize_GETINTERIORFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                descr = op.getdescr()
                fieldvalue = value.getinteriorfield(
                    indexbox.getint(), descr, self.new_const(descr)
                )
                self.make_equal_to(op.result, fieldvalue)
                return
        value.ensure_nonnull()
        self.emit_operation(op)

    def optimize_SETINTERIORFIELD_GC(self, op):
        value = self.getvalue(op.getarg(0))
        if value.is_virtual():
            indexbox = self.get_constant_box(op.getarg(1))
            if indexbox is not None:
                value.setinteriorfield(
                    indexbox.getint(), op.getdescr(), self.getvalue(op.getarg(2))
                )
                return
        value.ensure_nonnull()
        self.emit_operation(op)


dispatch_opt = make_dispatcher_method(OptVirtualize, 'optimize_',
        default=OptVirtualize.emit_operation)

OptVirtualize.propagate_forward = dispatch_opt
