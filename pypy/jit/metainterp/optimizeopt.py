from pypy.jit.metainterp.history import Box, BoxInt, BoxPtr, BoxObj
from pypy.jit.metainterp.history import Const, ConstInt, ConstPtr, ConstObj, PTR, OBJ
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.specnode import SpecNode, ConstantSpecNode
from pypy.jit.metainterp.specnode import AbstractVirtualStructSpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.specnode import VirtualArraySpecNode
from pypy.jit.metainterp.specnode import VirtualStructSpecNode
from pypy.jit.metainterp.optimizeutil import av_newdict2, _findall, sort_descrs
from pypy.jit.metainterp import resume, compile
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype

def optimize_loop_1(cpu, loop):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizer = Optimizer(cpu, loop)
    optimizer.setup_virtuals_and_constants()
    optimizer.propagate_forward()

def optimize_bridge_1(cpu, bridge):
    """The same, but for a bridge.  The only difference is that we don't
    expect 'specnodes' on the bridge.
    """
    optimizer = Optimizer(cpu, bridge)
    optimizer.propagate_forward()

# ____________________________________________________________

LEVEL_UNKNOWN    = 0
LEVEL_NONNULL    = 1
LEVEL_KNOWNCLASS = 2     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = 3


class OptValue(object):
    _attrs_ = ('box', 'level', '_fields')
    level = LEVEL_UNKNOWN
    _fields = None

    def __init__(self, box):
        self.box = box
        if isinstance(box, Const):
            self.level = LEVEL_CONSTANT

    def force_box(self):
        return self.box

    def get_key_box(self):
        return self.box

    def get_args_for_fail(self, modifier):
        pass

    def is_constant(self):
        return self.level == LEVEL_CONSTANT

    def is_null(self):
        return self.is_constant() and not self.box.nonnull()

    def make_constant(self):
        """Mark 'self' as actually representing a Const value."""
        self.box = self.force_box().constbox()
        self.level = LEVEL_CONSTANT

    def has_constant_class(self):
        return self.level >= LEVEL_KNOWNCLASS

    def make_constant_class(self):
        if self.level < LEVEL_KNOWNCLASS:
            self.level = LEVEL_KNOWNCLASS

    def is_nonnull(self):
        level = self.level
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            return self.box.nonnull()
        else:
            return False

    def make_nonnull(self):
        if self.level < LEVEL_NONNULL:
            self.level = LEVEL_NONNULL

    def make_null_or_nonnull(self):
        if self.box.nonnull():
            self.make_nonnull()
        else:
            self.make_constant()

    def is_virtual(self):
        # Don't check this with 'isinstance(_, VirtualValue)'!
        # Even if it is a VirtualValue, the 'box' can be non-None,
        # meaning it has been forced.
        return self.box is None

class BoolValue(OptValue):

    def __init__(self, box, fromvalue):
        OptValue.__init__(self, box)
        self.fromvalue = fromvalue

    def make_constant(self):
        OptValue.make_constant(self)
        self.fromvalue.make_null_or_nonnull()

class ConstantValue(OptValue):
    level = LEVEL_CONSTANT

    def __init__(self, box):
        self.box = box

CVAL_ZERO    = ConstantValue(ConstInt(0))
CVAL_NULLPTR = ConstantValue(ConstPtr(ConstPtr.value))
CVAL_NULLOBJ = ConstantValue(ConstObj(ConstObj.value))


class AbstractVirtualValue(OptValue):
    _attrs_ = ('optimizer', 'keybox', 'source_op')
    box = None
    level = LEVEL_KNOWNCLASS

    def __init__(self, optimizer, keybox, source_op=None):
        self.optimizer = optimizer
        self.keybox = keybox   # only used as a key in dictionaries
        self.source_op = source_op  # the NEW_WITH_VTABLE/NEW_ARRAY operation
                                    # that builds this box

    def get_key_box(self):
        if self.box is None:
            return self.keybox
        return self.box


class AbstractVirtualStructValue(AbstractVirtualValue):

    def __init__(self, optimizer, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, optimizer, keybox, source_op)
        self._fields = av_newdict2()

    def getfield(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        assert isinstance(fieldvalue, OptValue)
        self._fields[ofs] = fieldvalue

    def force_box(self):
        if self.box is None:
            if self.source_op is None:
                self.prepare_force_box()
            newoperations = self.optimizer.newoperations
            newoperations.append(self.source_op)
            self.box = box = self.source_op.result
            #
            iteritems = self._fields.iteritems()
            if not we_are_translated(): #random order is fine, except for tests
                iteritems = list(iteritems)
                iteritems.sort(key = lambda (x,y): x.sort_key())
            for ofs, value in iteritems:
                subbox = value.force_box()
                op = ResOperation(rop.SETFIELD_GC, [box, subbox], None,
                                  descr=ofs)
                newoperations.append(op)
            self._fields = None
        return self.box

    def prepare_force_box(self):
        raise NotImplementedError

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.is_virtual(self.keybox):
            # modifier.is_virtual() checks for recursion: it is False unless
            # we have already seen the very same keybox
            lst = self._fields.keys()
            sort_descrs(lst)
            fieldboxes = [self._fields[ofs].get_key_box() for ofs in lst]
            self._make_virtual(modifier, lst, fieldboxes)
            for ofs in lst:
                fieldvalue = self._fields[ofs]
                fieldvalue.get_args_for_fail(modifier)

    def _make_virtual(self, modifier, fielddescrs, fieldboxes):
        raise NotImplementedError


class VirtualValue(AbstractVirtualStructValue):

    def __init__(self, optimizer, known_class, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, optimizer, keybox, source_op)
        self.known_class = known_class

    def prepare_force_box(self):
        # rare case (shown by test_p123_simple) to force a Virtual
        # from a specnode computed by optimizefindnode.
        assert self.optimizer.reached_the_end
        # The previous check is done for safety reasons:
        # this function should only be used from teardown_virtual_node();
        # if we call force_box() from somewhere else and we get
        # source_op=None, it is really a bug.
        self.source_op = ResOperation(rop.NEW_WITH_VTABLE,
                                      [self.known_class],
                                      self.optimizer.new_ptr_box())

    def _make_virtual(self, modifier, fielddescrs, fieldboxes):
        modifier.make_virtual(self.keybox, self.known_class,
                              fielddescrs, fieldboxes)


class VStructValue(AbstractVirtualStructValue):

    def __init__(self, optimizer, structdescr, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, optimizer, keybox, source_op)
        self.structdescr = structdescr

    def prepare_force_box(self):
        # rare case (shown by test_p123_vstruct) to force a Virtual
        # from a specnode computed by optimizefindnode.
        assert self.optimizer.reached_the_end
        self.source_op = ResOperation(rop.NEW, [],
                                      self.optimizer.new_ptr_box(),
                                      descr=self.structdescr)

    def _make_virtual(self, modifier, fielddescrs, fieldboxes):
        modifier.make_vstruct(self.keybox, self.structdescr,
                              fielddescrs, fieldboxes)


class VArrayValue(AbstractVirtualValue):

    def __init__(self, optimizer, arraydescr, size, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, optimizer, keybox, source_op)
        self.arraydescr = arraydescr
        self._items = [None] * size

    def getlength(self):
        return len(self._items)

    def getitem(self, index, default):
        res = self._items[index]
        if res is None:
            res = default
        return res

    def setitem(self, index, itemvalue):
        assert isinstance(itemvalue, OptValue)
        self._items[index] = itemvalue

    def force_box(self):
        if self.box is None:
            if self.source_op is None:
                self.prepare_force_box()
            newoperations = self.optimizer.newoperations
            newoperations.append(self.source_op)
            self.box = box = self.source_op.result
            for index in range(len(self._items)):
                subvalue = self._items[index]
                if subvalue is not None:
                    subbox = subvalue.force_box()
                    op = ResOperation(rop.SETARRAYITEM_GC,
                                      [box, ConstInt(index), subbox], None,
                                      descr=self.arraydescr)
                    newoperations.append(op)
        return self.box

    def prepare_force_box(self):
        # rare case (shown by test_p123_varray) to force a VirtualArray
        # from a specnode computed by optimizefindnode.
        assert self.optimizer.reached_the_end
        self.source_op = ResOperation(rop.NEW_ARRAY,
                                      [ConstInt(self.getlength())],
                                      self.optimizer.new_ptr_box(),
                                      descr=self.arraydescr)

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.is_virtual(self.keybox):
            # modifier.is_virtual() checks for recursion: it is False unless
            # we have already seen the very same keybox
            itemboxes = []
            const = self.optimizer.new_const_item(self.arraydescr)
            for itemvalue in self._items:
                if itemvalue is None:
                    itemvalue = const
                itemboxes.append(itemvalue.get_key_box())
            modifier.make_varray(self.keybox, self.arraydescr, itemboxes)
            for itemvalue in self._items:
                if itemvalue is not None:
                    itemvalue.get_args_for_fail(modifier)


class __extend__(SpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        newinputargs.append(box)
    def setup_constant_node(self, optimizer, box):
        pass
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        newexitargs.append(value.force_box())

class __extend__(ConstantSpecNode):
    def setup_constant_node(self, optimizer, box):
        optimizer.make_constant(box)

class __extend__(AbstractVirtualStructSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vvalue = self._setup_virtual_node_1(optimizer, box)
        for ofs, subspecnode in self.fields:
            subbox = optimizer.new_box(ofs)
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
            vvalue.setfield(ofs, optimizer.getvalue(subbox))
    def _setup_virtual_node_1(self, optimizer, box):
        raise NotImplementedError
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        assert value.is_virtual()
        for ofs, subspecnode in self.fields:
            subvalue = value.getfield(ofs, optimizer.new_const(ofs))
            subspecnode.teardown_virtual_node(optimizer, subvalue, newexitargs)

class __extend__(VirtualInstanceSpecNode):
    def _setup_virtual_node_1(self, optimizer, box):
        return optimizer.make_virtual(self.known_class, box)

class __extend__(VirtualStructSpecNode):
    def _setup_virtual_node_1(self, optimizer, box):
        return optimizer.make_vstruct(self.typedescr, box)

class __extend__(VirtualArraySpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vvalue = optimizer.make_varray(self.arraydescr, len(self.items), box)
        for index in range(len(self.items)):
            subbox = optimizer.new_box_item(self.arraydescr)
            subspecnode = self.items[index]
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
            vvalue.setitem(index, optimizer.getvalue(subbox))
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        assert value.is_virtual()
        const = optimizer.new_const_item(self.arraydescr)
        for index in range(len(self.items)):
            subvalue = value.getitem(index, const)
            subspecnode = self.items[index]
            subspecnode.teardown_virtual_node(optimizer, subvalue, newexitargs)


class Optimizer(object):

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop
        self.values = {}
        self.values_to_clean = []    # OptValues to clean when we see an
                                     # operation with side-effects
        self.reached_the_end = False
        self.interned_ptrs = {}
        self.interned_objs = {}

    def getinterned(self, box):
        if not self.is_constant(box):
            return box
        if not self.cpu.is_oo and box.type == PTR:
            value = box.getptr_base()
            key = lltype.cast_ptr_to_int(value)
            try:
                return self.interned_ptrs[key]
            except KeyError:
                self.interned_ptrs[key] = box
                return box
        elif self.cpu.is_oo and box.type == OBJ:
            value = box.getobj()
            try:
                return self.interned_objs[value]
            except KeyError:
                self.interned_objs[value] = box
                return box
        else:
            return box
        

    def getvalue(self, box):
        box = self.getinterned(box)
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = OptValue(box)
        return value

    def is_constant(self, box):
        if isinstance(box, Const):
            return True
        try:
            return self.values[box].is_constant()
        except KeyError:
            return False

    def make_equal_to(self, box, value):
        assert box not in self.values
        self.values[box] = value

    def make_constant(self, box):
        self.make_equal_to(box, ConstantValue(box.constbox()))

    def known_nonnull(self, box):
        return self.getvalue(box).is_nonnull()

    def make_virtual(self, known_class, box, source_op=None):
        vvalue = VirtualValue(self, known_class, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_varray(self, arraydescr, size, box, source_op=None):
        vvalue = VArrayValue(self, arraydescr, size, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_vstruct(self, structdescr, box, source_op=None):
        vvalue = VStructValue(self, structdescr, box, source_op)
        self.make_equal_to(box, vvalue)
        return vvalue

    def make_bool(self, box, fromvalue):
        value = BoolValue(box, fromvalue)
        self.make_equal_to(box, value)
        return value

    def new_ptr_box(self):
        if not self.cpu.is_oo:
            return BoxPtr()
        else:
            return BoxObj()

    def new_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.new_ptr_box()
        else:
            return BoxInt()

    def new_const(self, fieldofs):
        if fieldofs.is_pointer_field():
            if not self.cpu.is_oo:
                return CVAL_NULLPTR
            else:
                return CVAL_NULLOBJ
        else:
            return CVAL_ZERO

    def new_box_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.new_ptr_box()
        else:
            return BoxInt()

    def new_const_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            if not self.cpu.is_oo:
                return CVAL_NULLPTR
            else:
                return CVAL_NULLOBJ
        else:
            return CVAL_ZERO

    # ----------

    def setup_virtuals_and_constants(self):
        inputargs = self.loop.inputargs
        specnodes = self.loop.specnodes
        assert len(inputargs) == len(specnodes)
        newinputargs = []
        for i in range(len(inputargs)):
            specnodes[i].setup_virtual_node(self, inputargs[i], newinputargs)
            specnodes[i].setup_constant_node(self, inputargs[i])
        self.loop.inputargs = newinputargs

    # ----------

    def propagate_forward(self):
        self.exception_might_have_happened = False
        self.newoperations = []
        for op in self.loop.operations:
            opnum = op.opnum
            for value, func in optimize_ops:
                if opnum == value:
                    func(self, op)
                    break
            else:
                self.optimize_default(op)
        self.loop.operations = self.newoperations

    def emit_operation(self, op, must_clone=True):
        op1 = op
        for i in range(len(op.args)):
            arg = op.args[i]
            if arg in self.values:
                box = self.values[arg].force_box()
                if box is not arg:
                    if must_clone:
                        op = op.clone()
                        must_clone = False
                    op.args[i] = box
        if op.is_guard():
            self.clone_guard(op, op1)
        elif op.can_raise():
            self.exception_might_have_happened = True
        self.newoperations.append(op)

    def clone_guard(self, op2, op1):
        assert len(op1.suboperations) == 1
        op_fail = op1.suboperations[0]
        assert op_fail.opnum == rop.FAIL
        #
        if not we_are_translated() and op_fail.descr is None:  # for tests
            descr = Storage()
            builder = resume.ResumeDataBuilder()
            builder.generate_boxes(op_fail.args)
            builder.finish(descr)
        else:
            descr = op_fail.descr
            assert isinstance(descr, compile.ResumeGuardDescr)
        oldboxes = []
        for box in op_fail.args:
            if box in self.values:
                box = self.values[box].get_key_box()   # may be a Const, too
            oldboxes.append(box)
        modifier = resume.ResumeDataVirtualAdder(descr, oldboxes)
        for box in op_fail.args:
            if box in self.values:
                value = self.values[box]
                value.get_args_for_fail(modifier)
        newboxes = modifier.finish()
        # XXX we mutate op_fail in-place below, as well as op_fail.descr
        # via the ResumeDataVirtualAdder.  That's bad.  Hopefully
        # it does not really matter because no-one is going to look again
        # at its unoptimized version.  We should really clone it (and
        # the descr too).
        op_fail.args = newboxes
        op2.suboperations = op1.suboperations
        op1.optimized = op2

    def optimize_default(self, op):
        if op.is_always_pure():
            for arg in op.args:
                if not self.is_constant(arg):
                    break
            else:
                # all constant arguments: constant-fold away
                self.make_constant(op.result)
                return
        elif not op.has_no_side_effect():
            for value in self.values_to_clean:
                value._fields.clear()
            del self.values_to_clean[:]
        # otherwise, the operation remains
        self.emit_operation(op)

    def optimize_JUMP(self, op):
        self.reached_the_end = True
        orgop = self.loop.operations[-1]
        exitargs = []
        specnodes = orgop.jump_target.specnodes
        assert len(op.args) == len(specnodes)
        for i in range(len(specnodes)):
            value = self.getvalue(op.args[i])
            specnodes[i].teardown_virtual_node(self, value, exitargs)
        op2 = op.clone()
        op2.args = exitargs
        op2.jump_target = op.jump_target
        self.emit_operation(op2, must_clone=False)

    def optimize_guard(self, op):
        value = self.getvalue(op.args[0])
        if value.is_constant():
            return
        self.emit_operation(op)
        value.make_constant()

    def optimize_GUARD_VALUE(self, op):
        assert isinstance(op.args[1], Const)
        assert op.args[0].get_() == op.args[1].get_()
        self.optimize_guard(op)

    def optimize_GUARD_TRUE(self, op):
        assert op.args[0].getint() == 1
        self.optimize_guard(op)

    def optimize_GUARD_FALSE(self, op):
        assert op.args[0].getint() == 0
        self.optimize_guard(op)

    def optimize_GUARD_CLASS(self, op):
        # XXX should probably assert that the class is right
        value = self.getvalue(op.args[0])
        if value.has_constant_class():
            return
        self.emit_operation(op)
        value.make_constant_class()

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if not self.exception_might_have_happened:
            return
        self.emit_operation(op)
        self.exception_might_have_happened = False

    def _optimize_nullness(self, op, expect_nonnull):
        if self.known_nonnull(op.args[0]):
            assert op.result.getint() == expect_nonnull
            self.make_constant(op.result)
        elif self.is_constant(op.args[0]): # known to be null
            assert op.result.getint() == (not expect_nonnull)
            self.make_constant(op.result)
        else:
            self.make_bool(op.result, self.getvalue(op.args[0]))
            self.emit_operation(op)

    def optimize_OONONNULL(self, op):
        self._optimize_nullness(op, True)

    def optimize_OOISNULL(self, op):
        self._optimize_nullness(op, False)

    def optimize_OOISNOT(self, op):
        value0 = self.getvalue(op.args[0])
        value1 = self.getvalue(op.args[1])
        if value0.is_virtual() or value1.is_virtual():
            self.make_constant(op.result)
        elif value1.is_null():
            op = ResOperation(rop.OONONNULL, [op.args[0]], op.result)
            self.optimize_OONONNULL(op)
        elif value0.is_null():
            op = ResOperation(rop.OONONNULL, [op.args[1]], op.result)
            self.optimize_OONONNULL(op)
        else:
            self.optimize_default(op)

    def optimize_OOIS(self, op):
        value0 = self.getvalue(op.args[0])
        value1 = self.getvalue(op.args[1])
        if value0.is_virtual() or value1.is_virtual():
            self.make_constant(op.result)
        elif value1.is_null():
            op = ResOperation(rop.OOISNULL, [op.args[0]], op.result)
            self.optimize_OOISNULL(op)
        elif value0.is_null():
            op = ResOperation(rop.OOISNULL, [op.args[1]], op.result)
            self.optimize_OOISNULL(op)
        else:
            self.optimize_default(op)

    def optimize_GETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            # optimizefindnode should ensure that fieldvalue is found
            fieldvalue = value.getfield(op.descr, None)
            assert fieldvalue is not None
            self.make_equal_to(op.result, fieldvalue)
        else:
            # check if the field was read from another getfield_gc just before
            if value._fields is None:
                value._fields = av_newdict2()
            elif op.descr in value._fields:
                self.make_equal_to(op.result, value._fields[op.descr])
                return
            # default case: produce the operation
            value.make_nonnull()
            self.optimize_default(op)
            # then remember the result of reading the field
            value._fields[op.descr] = self.getvalue(op.result)
            self.values_to_clean.append(value)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETFIELD_GC_PURE is_always_pure().
    optimize_GETFIELD_GC_PURE = optimize_GETFIELD_GC

    def optimize_SETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            value.setfield(op.descr, self.getvalue(op.args[1]))
        else:
            value.make_nonnull()
            self.optimize_default(op)
            # remember the result of future reads of the field
            if value._fields is None:
                value._fields = av_newdict2()
            value._fields[op.descr] = self.getvalue(op.args[1])
            self.values_to_clean.append(value)

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.args[0], op.result, op)

    def optimize_NEW(self, op):
        self.make_vstruct(op.descr, op.result, op)

    def optimize_NEW_ARRAY(self, op):
        sizebox = op.args[0]
        if self.is_constant(sizebox):
            size = sizebox.getint()
            if not isinstance(sizebox, ConstInt):
                op = ResOperation(rop.NEW_ARRAY, [ConstInt(size)], op.result,
                                  descr=op.descr)
            self.make_varray(op.descr, size, op.result, op)
        else:
            self.optimize_default(op)

    def optimize_ARRAYLEN_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            assert op.result.getint() == value.getlength()
            self.make_constant(op.result)
        else:
            value.make_nonnull()
            self.optimize_default(op)

    def optimize_GETARRAYITEM_GC(self, op):
        value = self.getvalue(op.args[0])
        indexbox = op.args[1]
        if value.is_virtual() and self.is_constant(indexbox):
            # optimizefindnode should ensure that itemvalue is found
            itemvalue = value.getitem(indexbox.getint(), None)
            assert itemvalue is not None
            self.make_equal_to(op.result, itemvalue)
        else:
            value.make_nonnull()
            self.optimize_default(op)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETARRAYITEM_GC_PURE is_always_pure().
    optimize_GETARRAYITEM_GC_PURE = optimize_GETARRAYITEM_GC

    def optimize_SETARRAYITEM_GC(self, op):
        value = self.getvalue(op.args[0])
        indexbox = op.args[1]
        if value.is_virtual() and self.is_constant(indexbox):
            value.setitem(indexbox.getint(), self.getvalue(op.args[2]))
        else:
            value.make_nonnull()
            self.optimize_default(op)

    def optimize_INSTANCEOF(self, op):
        value = self.getvalue(op.args[0])
        if value.has_constant_class():
            self.make_constant(op.result)
            return
        self.emit_operation(op)

    def optimize_DEBUG_MERGE_POINT(self, op):
        # special-case this operation to prevent e.g. the handling of
        # 'values_to_clean' (the op cannot be marked as side-effect-free)
        self.newoperations.append(op)

optimize_ops = _findall(Optimizer, 'optimize_')

class Storage:
    "for tests."
