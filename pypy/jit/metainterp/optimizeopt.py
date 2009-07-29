from pypy.jit.metainterp.history import Box, BoxInt, BoxPtr, BoxObj
from pypy.jit.metainterp.history import Const, ConstInt, ConstPtr, ConstObj
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.specnode import SpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.optimizeutil import av_newdict2, _findall, sort_descrs
from pypy.jit.metainterp import resume, compile
from pypy.rlib.objectmodel import we_are_translated


def optimize_loop_1(cpu, loop):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizer = Optimizer(cpu, loop)
    optimizer.setup_virtuals()
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


class InstanceValue(object):
    _attrs_ = ('box', 'level')
    level = LEVEL_UNKNOWN

    def __init__(self, box):
        self.box = box
        if isinstance(box, Const):
            self.level = LEVEL_CONSTANT

    def force_box(self):
        return self.box

    def prepare_force_box(self):
        pass

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

    def is_virtual(self):
        # Don't check this with 'isinstance(_, VirtualValue)'!
        # Even if it is a VirtualValue, the 'box' can be non-None,
        # meaning it has been forced.
        return self.box is None


class ConstantValue(InstanceValue):
    level = LEVEL_CONSTANT

    def __init__(self, box):
        self.box = box

CVAL_ZERO    = ConstantValue(ConstInt(0))
CVAL_NULLPTR = ConstantValue(ConstPtr(ConstPtr.value))
CVAL_NULLOBJ = ConstantValue(ConstObj(ConstObj.value))


class AbstractVirtualValue(InstanceValue):
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


class VirtualValue(AbstractVirtualValue):

    def __init__(self, optimizer, known_class, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, optimizer, keybox, source_op)
        self.known_class = known_class
        self._fields = av_newdict2()

    def getfield(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        assert isinstance(fieldvalue, InstanceValue)
        self._fields[ofs] = fieldvalue

    def force_box(self):
        if self.box is None:
            assert self.source_op is not None       # otherwise, we are trying
            # to force a Virtual from a specnode computed by optimizefindnode.
            newoperations = self.optimizer.newoperations
            newoperations.append(self.source_op)
            self.box = box = self.source_op.result
            for ofs in self._fields:
                subbox = self._fields[ofs].force_box()
                op = ResOperation(rop.SETFIELD_GC, [box, subbox], None,
                                  descr=ofs)
                newoperations.append(op)
        return self.box

    def prepare_force_box(self):
        # This logic is not included in force_box() for safety reasons.
        # It should only be used from teardown_virtual_node(); if we
        # call force_box() from somewhere else and we get source_op=None,
        # it is really a bug.
        if self.box is None and self.source_op is None:
            # rare case (shown by test_p123_simple) to force a Virtual
            # from a specnode computed by optimizefindnode.
            self.source_op = ResOperation(rop.NEW_WITH_VTABLE,
                                          [self.known_class],
                                          self.optimizer.new_ptr_box())

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.is_virtual(self.keybox):
            lst = self._fields.keys()
            sort_descrs(lst)
            fieldboxes = [self._fields[ofs].get_key_box() for ofs in lst]
            modifier.make_virtual(self.keybox, self.known_class,
                                  lst, fieldboxes)
            for ofs in lst:
                fieldvalue = self._fields[ofs]
                fieldvalue.get_args_for_fail(modifier)


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
        assert isinstance(itemvalue, InstanceValue)
        self._items[index] = itemvalue

    def force_box(self):
        if self.box is None:
            assert self.source_op is not None       # otherwise, we are trying
            # to force a VArray from a specnode computed by optimizefindnode.
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
        # This logic is not included in force_box() for safety reasons.
        # It should only be used from teardown_virtual_node(); if we
        # call force_box() from somewhere else and we get source_op=None,
        # it is really a bug.
        XXX
        if self.box is None and self.source_op is None:
            # rare case (shown by test_p123_simple) to force a Virtual
            # from a specnode computed by optimizefindnode.
            self.source_op = ResOperation(rop.NEW_WITH_VTABLE,
                                          [self.known_class],
                                          self.optimizer.new_ptr_box())

    def get_args_for_fail(self, modifier):
        XXX
        if self.box is None and not modifier.is_virtual(self.keybox):
            lst = self._fields.keys()
            sort_descrs(lst)
            fieldboxes = [self._fields[ofs].get_key_box() for ofs in lst]
            modifier.make_virtual(self.keybox, self.known_class,
                                  lst, fieldboxes)
            for ofs in lst:
                fieldvalue = self._fields[ofs]
                fieldvalue.get_args_for_fail(modifier)


class __extend__(SpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        newinputargs.append(box)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        value.prepare_force_box()
        newexitargs.append(value.force_box())

class __extend__(VirtualInstanceSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vvalue = optimizer.make_virtual(self.known_class, box)
        for ofs, subspecnode in self.fields:
            subbox = optimizer.new_box(ofs)
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
            vvalue.setfield(ofs, optimizer.getvalue(subbox))
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        assert value.is_virtual()
        for ofs, subspecnode in self.fields:
            subvalue = value.getfield(ofs, optimizer.new_const(ofs))
            subspecnode.teardown_virtual_node(optimizer, subvalue, newexitargs)


class Optimizer(object):

    def __init__(self, cpu, loop):
        self.cpu = cpu
        self.loop = loop
        self.values = {}

    def getvalue(self, box):
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = InstanceValue(box)
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

    # ----------

    def setup_virtuals(self):
        inputargs = self.loop.inputargs
        specnodes = self.loop.specnodes
        assert len(inputargs) == len(specnodes)
        newinputargs = []
        for i in range(len(inputargs)):
            specnodes[i].setup_virtual_node(self, inputargs[i], newinputargs)
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
        # otherwise, the operation remains
        self.emit_operation(op)

    def optimize_JUMP(self, op):
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

    def optimize_OONONNULL(self, op):
        if self.known_nonnull(op.args[0]):
            assert op.result.getint() == 1
            self.make_constant(op.result)
        else:
            self.optimize_default(op)

    def optimize_OOISNULL(self, op):
        if self.known_nonnull(op.args[0]):
            assert op.result.getint() == 0
            self.make_constant(op.result)
        else:
            self.optimize_default(op)

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
            value.make_nonnull()
            self.optimize_default(op)

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

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.args[0], op.result, op)

    def optimize_NEW_ARRAY(self, op):
        sizebox = op.args[0]
        if self.is_constant(sizebox):
            self.make_varray(op.descr, sizebox.getint(), op.result, op)
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


optimize_ops = _findall(Optimizer, 'optimize_')

class Storage:
    "for tests."
