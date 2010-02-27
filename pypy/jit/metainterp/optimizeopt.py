from pypy.jit.metainterp.history import Box, BoxInt, LoopToken, BoxFloat,\
     ConstFloat
from pypy.jit.metainterp.history import Const, ConstInt, ConstPtr, ConstObj, REF
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp import jitprof
from pypy.jit.metainterp.executor import execute_nonspec
from pypy.jit.metainterp.specnode import SpecNode, NotSpecNode, ConstantSpecNode
from pypy.jit.metainterp.specnode import AbstractVirtualStructSpecNode
from pypy.jit.metainterp.specnode import VirtualInstanceSpecNode
from pypy.jit.metainterp.specnode import VirtualArraySpecNode
from pypy.jit.metainterp.specnode import VirtualStructSpecNode
from pypy.jit.metainterp.optimizeutil import _findall, sort_descrs
from pypy.jit.metainterp.optimizeutil import descrlist_dict
from pypy.jit.metainterp.optimizeutil import InvalidLoop, args_dict
from pypy.jit.metainterp import resume, compile
from pypy.jit.metainterp.typesystem import llhelper, oohelper
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype

def optimize_loop_1(metainterp_sd, loop):
    """Optimize loop.operations to make it match the input of loop.specnodes
    and to remove internal overheadish operations.  Note that loop.specnodes
    must be applicable to the loop; you will probably get an AssertionError
    if not.
    """
    optimizer = Optimizer(metainterp_sd, loop)
    optimizer.setup_virtuals_and_constants()
    optimizer.propagate_forward()

def optimize_bridge_1(metainterp_sd, bridge):
    """The same, but for a bridge.  The only difference is that we don't
    expect 'specnodes' on the bridge.
    """
    optimizer = Optimizer(metainterp_sd, bridge)
    optimizer.propagate_forward()

# ____________________________________________________________

LEVEL_UNKNOWN    = '\x00'
LEVEL_NONNULL    = '\x01'
LEVEL_KNOWNCLASS = '\x02'     # might also mean KNOWNARRAYDESCR, for arrays
LEVEL_CONSTANT   = '\x03'


class OptValue(object):
    _attrs_ = ('box', 'known_class', 'last_guard_index', 'level')
    last_guard_index = -1

    level = LEVEL_UNKNOWN

    def __init__(self, box):
        self.box = box
        if isinstance(box, Const):
            self.level = LEVEL_CONSTANT
        # invariant: box is a Const if and only if level == LEVEL_CONSTANT

    def force_box(self):
        return self.box

    def get_key_box(self):
        return self.box

    def get_args_for_fail(self, modifier):
        pass

    def make_virtual_info(self, modifier, fieldnums):
        raise NotImplementedError # should not be called on this level

    def is_constant(self):
        return self.level == LEVEL_CONSTANT

    def is_null(self):
        if self.is_constant():
            box = self.box
            assert isinstance(box, Const)
            return not box.nonnull()
        return False

    def make_constant(self, constbox):
        """Replace 'self.box' with a Const box."""
        assert isinstance(constbox, Const)
        self.box = constbox
        self.level = LEVEL_CONSTANT

    def get_constant_class(self, cpu):
        level = self.level
        if level == LEVEL_KNOWNCLASS:
            return self.known_class
        elif level == LEVEL_CONSTANT:
            return cpu.ts.cls_of_box(cpu, self.box)
        else:
            return None

    def make_constant_class(self, classbox, opindex):
        assert self.level < LEVEL_KNOWNCLASS
        self.known_class = classbox
        self.level = LEVEL_KNOWNCLASS
        self.last_guard_index = opindex

    def make_nonnull(self, opindex):
        assert self.level < LEVEL_NONNULL
        self.level = LEVEL_NONNULL
        self.last_guard_index = opindex

    def is_nonnull(self):
        level = self.level
        if level == LEVEL_NONNULL or level == LEVEL_KNOWNCLASS:
            return True
        elif level == LEVEL_CONSTANT:
            box = self.box
            assert isinstance(box, Const)
            return box.nonnull()
        else:
            return False

    def ensure_nonnull(self):
        if self.level < LEVEL_NONNULL:
            self.level = LEVEL_NONNULL

    def is_virtual(self):
        # Don't check this with 'isinstance(_, VirtualValue)'!
        # Even if it is a VirtualValue, the 'box' can be non-None,
        # meaning it has been forced.
        return self.box is None

class ConstantValue(OptValue):
    level = LEVEL_CONSTANT

    def __init__(self, box):
        self.box = box

CONST_0      = ConstInt(0)
CONST_1      = ConstInt(1)
CVAL_ZERO    = ConstantValue(CONST_0)
CVAL_ZERO_FLOAT = ConstantValue(ConstFloat(0.0))
llhelper.CVAL_NULLREF = ConstantValue(llhelper.CONST_NULL)
oohelper.CVAL_NULLREF = ConstantValue(oohelper.CONST_NULL)


class AbstractVirtualValue(OptValue):
    _attrs_ = ('optimizer', 'keybox', 'source_op', '_cached_vinfo')
    box = None
    level = LEVEL_NONNULL
    _cached_vinfo = None

    def __init__(self, optimizer, keybox, source_op=None):
        self.optimizer = optimizer
        self.keybox = keybox   # only used as a key in dictionaries
        self.source_op = source_op  # the NEW_WITH_VTABLE/NEW_ARRAY operation
                                    # that builds this box

    def get_key_box(self):
        if self.box is None:
            return self.keybox
        return self.box

    def force_box(self):
        if self.box is None:
            self.optimizer.forget_numberings(self.keybox)
            self._really_force()
        return self.box

    def make_virtual_info(self, modifier, fieldnums):
        vinfo = self._cached_vinfo
        if vinfo is not None and vinfo.equals(fieldnums):
            return vinfo
        vinfo = self._make_virtual(modifier)
        vinfo.set_content(fieldnums)
        self._cached_vinfo = vinfo
        return vinfo

    def _make_virtual(self, modifier):
        raise NotImplementedError("abstract base")


def get_fielddescrlist_cache(cpu):
    if not hasattr(cpu, '_optimizeopt_fielddescrlist_cache'):
        result = descrlist_dict()
        cpu._optimizeopt_fielddescrlist_cache = result
        return result
    return cpu._optimizeopt_fielddescrlist_cache
get_fielddescrlist_cache._annspecialcase_ = "specialize:memo"

class AbstractVirtualStructValue(AbstractVirtualValue):
    _attrs_ = ('_fields', '_cached_sorted_fields')

    def __init__(self, optimizer, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, optimizer, keybox, source_op)
        self._fields = {}
        self._cached_sorted_fields = None

    def getfield(self, ofs, default):
        return self._fields.get(ofs, default)

    def setfield(self, ofs, fieldvalue):
        assert isinstance(fieldvalue, OptValue)
        self._fields[ofs] = fieldvalue

    def _really_force(self):
        if self.source_op is None:
            # this case should not occur; I only managed to get it once
            # in pypy-c-jit and couldn't reproduce it.  The point is
            # that it relies on optimizefindnode.py computing exactly
            # the right level of specialization, and it seems that there
            # is still a corner case where it gets too specialized for
            # optimizeopt.py.  Let's not crash in release-built
            # pypy-c-jit's.  XXX find out when
            from pypy.rlib.debug import ll_assert
            ll_assert(False, "_really_force: source_op is None")
            raise InvalidLoop
        #
        newoperations = self.optimizer.newoperations
        newoperations.append(self.source_op)
        self.box = box = self.source_op.result
        #
        iteritems = self._fields.iteritems()
        if not we_are_translated(): #random order is fine, except for tests
            iteritems = list(iteritems)
            iteritems.sort(key = lambda (x,y): x.sort_key())
        for ofs, value in iteritems:
            if value.is_null():
                continue
            subbox = value.force_box()
            op = ResOperation(rop.SETFIELD_GC, [box, subbox], None,
                              descr=ofs)
            newoperations.append(op)
        self._fields = None

    def _get_field_descr_list(self):
        _cached_sorted_fields = self._cached_sorted_fields
        if (_cached_sorted_fields is not None and
            len(self._fields) == len(_cached_sorted_fields)):
            lst = self._cached_sorted_fields
        else:
            lst = self._fields.keys()
            sort_descrs(lst)
            cache = get_fielddescrlist_cache(self.optimizer.cpu)
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
    level = LEVEL_KNOWNCLASS

    def __init__(self, optimizer, known_class, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, optimizer, keybox, source_op)
        assert isinstance(known_class, Const)
        self.known_class = known_class

    def _make_virtual(self, modifier):
        fielddescrs = self._get_field_descr_list()
        return modifier.make_virtual(self.known_class, fielddescrs)

class VStructValue(AbstractVirtualStructValue):

    def __init__(self, optimizer, structdescr, keybox, source_op=None):
        AbstractVirtualStructValue.__init__(self, optimizer, keybox, source_op)
        self.structdescr = structdescr

    def _make_virtual(self, modifier):
        fielddescrs = self._get_field_descr_list()
        return modifier.make_vstruct(self.structdescr, fielddescrs)

class VArrayValue(AbstractVirtualValue):

    def __init__(self, optimizer, arraydescr, size, keybox, source_op=None):
        AbstractVirtualValue.__init__(self, optimizer, keybox, source_op)
        self.arraydescr = arraydescr
        self.constvalue = optimizer.new_const_item(arraydescr)
        self._items = [self.constvalue] * size

    def getlength(self):
        return len(self._items)

    def getitem(self, index):
        res = self._items[index]
        return res

    def setitem(self, index, itemvalue):
        assert isinstance(itemvalue, OptValue)
        self._items[index] = itemvalue

    def _really_force(self):
        assert self.source_op is not None
        newoperations = self.optimizer.newoperations
        newoperations.append(self.source_op)
        self.box = box = self.source_op.result
        for index in range(len(self._items)):
            subvalue = self._items[index]
            if subvalue is not self.constvalue:
                if subvalue.is_null():
                    continue
                subbox = subvalue.force_box()
                op = ResOperation(rop.SETARRAYITEM_GC,
                                  [box, ConstInt(index), subbox], None,
                                  descr=self.arraydescr)
                newoperations.append(op)

    def get_args_for_fail(self, modifier):
        if self.box is None and not modifier.already_seen_virtual(self.keybox):
            # checks for recursion: it is False unless
            # we have already seen the very same keybox
            itemboxes = []
            for itemvalue in self._items:
                itemboxes.append(itemvalue.get_key_box())
            modifier.register_virtual_fields(self.keybox, itemboxes)
            for itemvalue in self._items:
                if itemvalue is not self.constvalue:
                    itemvalue.get_args_for_fail(modifier)

    def _make_virtual(self, modifier):
        return modifier.make_varray(self.arraydescr)

class __extend__(SpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        raise NotImplementedError
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        raise NotImplementedError

class __extend__(NotSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        newinputargs.append(box)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        newexitargs.append(value.force_box())

class __extend__(ConstantSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        optimizer.make_constant(box, self.constbox)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        pass

class __extend__(AbstractVirtualStructSpecNode):
    def setup_virtual_node(self, optimizer, box, newinputargs):
        vvalue = self._setup_virtual_node_1(optimizer, box)
        for ofs, subspecnode in self.fields:
            subbox = optimizer.new_box(ofs)
            subspecnode.setup_virtual_node(optimizer, subbox, newinputargs)
            vvaluefield = optimizer.getvalue(subbox)
            vvalue.setfield(ofs, vvaluefield)
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
            vvalueitem = optimizer.getvalue(subbox)
            vvalue.setitem(index, vvalueitem)
    def teardown_virtual_node(self, optimizer, value, newexitargs):
        assert value.is_virtual()
        for index in range(len(self.items)):
            subvalue = value.getitem(index)
            subspecnode = self.items[index]
            subspecnode.teardown_virtual_node(optimizer, subvalue, newexitargs)


class Optimizer(object):

    def __init__(self, metainterp_sd, loop):
        self.metainterp_sd = metainterp_sd
        self.cpu = metainterp_sd.cpu
        self.loop = loop
        self.values = {}
        self.interned_refs = self.cpu.ts.new_ref_dict()
        self.resumedata_memo = resume.ResumeDataLoopMemo(metainterp_sd)
        self.heap_op_optimizer = HeapOpOptimizer(self)
        self.bool_boxes = {}
        self.loop_invariant_results = {}
        self.pure_operations = args_dict()

    def forget_numberings(self, virtualbox):
        self.metainterp_sd.profiler.count(jitprof.OPT_FORCINGS)
        self.resumedata_memo.forget_numberings(virtualbox)

    def getinterned(self, box):
        constbox = self.get_constant_box(box)
        if constbox is None:
            return box
        if constbox.type == REF:
            value = constbox.getref_base()
            if not value:
                return box
            return self.interned_refs.setdefault(value, box)
        else:
            return box

    def getvalue(self, box):
        box = self.getinterned(box)
        try:
            value = self.values[box]
        except KeyError:
            value = self.values[box] = OptValue(box)
        return value

    def get_constant_box(self, box):
        if isinstance(box, Const):
            return box
        try:
            value = self.values[box]
        except KeyError:
            return None
        if value.is_constant():
            constbox = value.box
            assert isinstance(constbox, Const)
            return constbox
        return None

    def make_equal_to(self, box, value):
        assert box not in self.values
        self.values[box] = value

    def make_constant(self, box, constbox):
        self.make_equal_to(box, ConstantValue(constbox))

    def make_constant_int(self, box, intvalue):
        self.make_constant(box, ConstInt(intvalue))

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

    def new_ptr_box(self):
        return self.cpu.ts.BoxRef()

    def new_box(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.new_ptr_box()
        elif fieldofs.is_float_field():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const(self, fieldofs):
        if fieldofs.is_pointer_field():
            return self.cpu.ts.CVAL_NULLREF
        elif fieldofs.is_float_field():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    def new_box_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.new_ptr_box()
        elif arraydescr.is_array_of_floats():
            return BoxFloat()
        else:
            return BoxInt()

    def new_const_item(self, arraydescr):
        if arraydescr.is_array_of_pointers():
            return self.cpu.ts.CVAL_NULLREF
        elif arraydescr.is_array_of_floats():
            return CVAL_ZERO_FLOAT
        else:
            return CVAL_ZERO

    # ----------

    def setup_virtuals_and_constants(self):
        inputargs = self.loop.inputargs
        specnodes = self.loop.token.specnodes
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
        # accumulate counters
        self.resumedata_memo.update_counters(self.metainterp_sd.profiler)

    def emit_operation(self, op):
        self.heap_op_optimizer.emitting_operation(op)
        self._emit_operation(op)

    def _emit_operation(self, op):
        for i in range(len(op.args)):
            arg = op.args[i]
            if arg in self.values:
                box = self.values[arg].force_box()
                op.args[i] = box
        self.metainterp_sd.profiler.count(jitprof.OPT_OPS)
        if op.is_guard():
            self.metainterp_sd.profiler.count(jitprof.OPT_GUARDS)
            self.store_final_boxes_in_guard(op)
        elif op.can_raise():
            self.exception_might_have_happened = True
        elif op.returns_bool_result():
            self.bool_boxes[op.result] = None
        self.newoperations.append(op)

    def store_final_boxes_in_guard(self, op):
        pendingfields = self.heap_op_optimizer.force_lazy_setfields_for_guard()
        descr = op.descr
        assert isinstance(descr, compile.ResumeGuardDescr)
        modifier = resume.ResumeDataVirtualAdder(descr, self.resumedata_memo)
        newboxes = modifier.finish(self.values, pendingfields)
        if len(newboxes) > self.metainterp_sd.options.failargs_limit: # XXX be careful here
            raise compile.GiveUp
        descr.store_final_boxes(op, newboxes)
        #
        if op.opnum == rop.GUARD_VALUE:
            if op.args[0] in self.bool_boxes:
                # Hack: turn guard_value(bool) into guard_true/guard_false.
                # This is done after the operation is emitted, to let
                # store_final_boxes_in_guard set the guard_opnum field
                # of the descr to the original rop.GUARD_VALUE.
                constvalue = op.args[1].getint()
                if constvalue == 0:
                    opnum = rop.GUARD_FALSE
                elif constvalue == 1:
                    opnum = rop.GUARD_TRUE
                else:
                    raise AssertionError("uh?")
                op.opnum = opnum
                op.args = [op.args[0]]
            else:
                # a real GUARD_VALUE.  Make it use one counter per value.
                descr.make_a_counter_per_value(op)

    def optimize_default(self, op):
        if op.is_always_pure():
            for arg in op.args:
                if self.get_constant_box(arg) is None:
                    break
            else:
                # all constant arguments: constant-fold away
                argboxes = [self.get_constant_box(arg) for arg in op.args]
                resbox = execute_nonspec(self.cpu, op.opnum, argboxes, op.descr)
                self.make_constant(op.result, resbox.constbox())
                return

            # did we do the exact same operation already?
            args = op.args[:]
            for i in range(len(args)):
                arg = args[i]
                if arg in self.values:
                    args[i] = self.values[arg].get_key_box()
            args.append(ConstInt(op.opnum))
            oldop = self.pure_operations.get(args, None)
            if oldop is not None and oldop.descr is op.descr:
                assert oldop.opnum == op.opnum
                self.make_equal_to(op.result, self.getvalue(oldop.result))
                return
            else:
                self.pure_operations[args] = op

        # otherwise, the operation remains
        self.emit_operation(op)

    def optimize_JUMP(self, op):
        orgop = self.loop.operations[-1]
        exitargs = []
        target_loop_token = orgop.descr
        assert isinstance(target_loop_token, LoopToken)
        specnodes = target_loop_token.specnodes
        assert len(op.args) == len(specnodes)
        for i in range(len(specnodes)):
            value = self.getvalue(op.args[i])
            specnodes[i].teardown_virtual_node(self, value, exitargs)
        op.args = exitargs[:]
        self.emit_operation(op)

    def optimize_guard(self, op, constbox, emit_operation=True):
        value = self.getvalue(op.args[0])
        if value.is_constant():
            box = value.box
            assert isinstance(box, Const)
            if not box.same_constant(constbox):
                raise InvalidLoop
            return
        if emit_operation:
            self.emit_operation(op)
        value.make_constant(constbox)

    def optimize_GUARD_ISNULL(self, op):
        value = self.getvalue(op.args[0])
        if value.is_null():
            return
        elif value.is_nonnull():
            raise InvalidLoop
        self.emit_operation(op)
        value.make_constant(self.cpu.ts.CONST_NULL)

    def optimize_GUARD_NONNULL(self, op):
        value = self.getvalue(op.args[0])
        if value.is_nonnull():
            return
        elif value.is_null():
            raise InvalidLoop
        self.emit_operation(op)
        value.make_nonnull(len(self.newoperations) - 1)

    def optimize_GUARD_VALUE(self, op):
        value = self.getvalue(op.args[0])
        emit_operation = True
        if value.last_guard_index != -1:
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value, which is rather silly.
            # replace the original guard with a guard_value
            old_guard_op = self.newoperations[value.last_guard_index]
            old_opnum = old_guard_op.opnum
            old_guard_op.opnum = rop.GUARD_VALUE
            old_guard_op.args = [old_guard_op.args[0], op.args[1]]
            # hack hack hack.  Change the guard_opnum on
            # old_guard_op.descr so that when resuming,
            # the operation is not skipped by pyjitpl.py.
            descr = old_guard_op.descr
            assert isinstance(descr, compile.ResumeGuardDescr)
            descr.guard_opnum = rop.GUARD_VALUE
            descr.make_a_counter_per_value(old_guard_op)
            emit_operation = False
        constbox = op.args[1]
        assert isinstance(constbox, Const)
        self.optimize_guard(op, constbox, emit_operation)

    def optimize_GUARD_TRUE(self, op):
        self.optimize_guard(op, CONST_1)

    def optimize_GUARD_FALSE(self, op):
        self.optimize_guard(op, CONST_0)

    def optimize_GUARD_CLASS(self, op):
        value = self.getvalue(op.args[0])
        expectedclassbox = op.args[1]
        assert isinstance(expectedclassbox, Const)
        realclassbox = value.get_constant_class(self.cpu)
        if realclassbox is not None:
            # the following assert should always be true for now,
            # because invalid loops that would fail it are detected
            # earlier, in optimizefindnode.py.
            assert realclassbox.same_constant(expectedclassbox)
            return
        emit_operation = True
        if value.last_guard_index != -1:
            # there already has been a guard_nonnull or guard_class or
            # guard_nonnull_class on this value.
            old_guard_op = self.newoperations[value.last_guard_index]
            if old_guard_op.opnum == rop.GUARD_NONNULL:
                # it was a guard_nonnull, which we replace with a
                # guard_nonnull_class.
                old_guard_op.opnum = rop.GUARD_NONNULL_CLASS
                old_guard_op.args = [old_guard_op.args[0], op.args[1]]
                # hack hack hack.  Change the guard_opnum on
                # old_guard_op.descr so that when resuming,
                # the operation is not skipped by pyjitpl.py.
                descr = old_guard_op.descr
                assert isinstance(descr, compile.ResumeGuardDescr)
                descr.guard_opnum = rop.GUARD_NONNULL_CLASS
                emit_operation = False
        if emit_operation:
            self.emit_operation(op)
            last_guard_index = len(self.newoperations) - 1
        else:
            last_guard_index = value.last_guard_index
        value.make_constant_class(expectedclassbox, last_guard_index)

    def optimize_GUARD_NO_EXCEPTION(self, op):
        if not self.exception_might_have_happened:
            return
        self.emit_operation(op)
        self.exception_might_have_happened = False

    def optimize_GUARD_NO_OVERFLOW(self, op):
        # otherwise the default optimizer will clear fields, which is unwanted
        # in this case
        self.emit_operation(op)


    def _optimize_nullness(self, op, box, expect_nonnull):
        value = self.getvalue(box)
        if value.is_nonnull():
            self.make_constant_int(op.result, expect_nonnull)
        elif value.is_null():
            self.make_constant_int(op.result, not expect_nonnull)
        else:
            self.optimize_default(op)

    def optimize_INT_IS_TRUE(self, op):
        self._optimize_nullness(op, op.args[0], True)

    def _optimize_oois_ooisnot(self, op, expect_isnot):
        value0 = self.getvalue(op.args[0])
        value1 = self.getvalue(op.args[1])
        if value0.is_virtual():
            if value1.is_virtual():
                intres = (value0 is value1) ^ expect_isnot
                self.make_constant_int(op.result, intres)
            else:
                self.make_constant_int(op.result, expect_isnot)
        elif value1.is_virtual():
            self.make_constant_int(op.result, expect_isnot)
        elif value1.is_null():
            self._optimize_nullness(op, op.args[0], expect_isnot)
        elif value0.is_null():
            self._optimize_nullness(op, op.args[1], expect_isnot)
        elif value0 is value1:
            self.make_constant_int(op.result, not expect_isnot)
        else:
            cls0 = value0.get_constant_class(self.cpu)
            if cls0 is not None:
                cls1 = value1.get_constant_class(self.cpu)
                if cls1 is not None and not cls0.same_constant(cls1):
                    # cannot be the same object, as we know that their
                    # class is different
                    self.make_constant_int(op.result, expect_isnot)
                    return
            self.optimize_default(op)

    def optimize_OOISNOT(self, op):
        self._optimize_oois_ooisnot(op, True)

    def optimize_OOIS(self, op):
        self._optimize_oois_ooisnot(op, False)

    def optimize_VIRTUAL_REF(self, op):
        indexbox = op.args[1]
        #
        # get some constants
        vrefinfo = self.metainterp_sd.virtualref_info
        c_cls = vrefinfo.jit_virtual_ref_const_class
        descr_virtual_token = vrefinfo.descr_virtual_token
        descr_virtualref_index = vrefinfo.descr_virtualref_index
        #
        # Replace the VIRTUAL_REF operation with a virtual structure of type
        # 'jit_virtual_ref'.  The jit_virtual_ref structure may be forced soon,
        # but the point is that doing so does not force the original structure.
        op = ResOperation(rop.NEW_WITH_VTABLE, [c_cls], op.result)
        vrefvalue = self.make_virtual(c_cls, op.result, op)
        tokenbox = BoxInt()
        self.emit_operation(ResOperation(rop.FORCE_TOKEN, [], tokenbox))
        vrefvalue.setfield(descr_virtual_token, self.getvalue(tokenbox))
        vrefvalue.setfield(descr_virtualref_index, self.getvalue(indexbox))

    def optimize_VIRTUAL_REF_FINISH(self, op):
        # Set the 'forced' field of the virtual_ref.
        # In good cases, this is all virtual, so has no effect.
        # Otherwise, this forces the real object -- but only now, as
        # opposed to much earlier.  This is important because the object is
        # typically a PyPy PyFrame, and now is the end of its execution, so
        # forcing it now does not have catastrophic effects.
        vrefinfo = self.metainterp_sd.virtualref_info
        # op.args[1] should really never point to null here
        # - set 'forced' to point to the real object
        op1 = ResOperation(rop.SETFIELD_GC, op.args, None,
                          descr = vrefinfo.descr_forced)
        self.optimize_SETFIELD_GC(op1)
        # - set 'virtual_token' to TOKEN_NONE
        args = [op.args[0], ConstInt(vrefinfo.TOKEN_NONE)]
        op1 = ResOperation(rop.SETFIELD_GC, args, None,
                      descr = vrefinfo.descr_virtual_token)
        self.optimize_SETFIELD_GC(op1)
        # Note that in some cases the virtual in op.args[1] has been forced
        # already.  This is fine.  In that case, and *if* a residual
        # CALL_MAY_FORCE suddenly turns out to access it, then it will
        # trigger a ResumeGuardForcedDescr.handle_async_forcing() which
        # will work too (but just be a little pointless, as the structure
        # was already forced).

    def optimize_GETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            # optimizefindnode should ensure that fieldvalue is found
            fieldvalue = value.getfield(op.descr, None)
            assert fieldvalue is not None
            self.make_equal_to(op.result, fieldvalue)
        else:
            value.ensure_nonnull()
            self.heap_op_optimizer.optimize_GETFIELD_GC(op, value)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETFIELD_GC_PURE is_always_pure().
    optimize_GETFIELD_GC_PURE = optimize_GETFIELD_GC

    def optimize_SETFIELD_GC(self, op):
        value = self.getvalue(op.args[0])
        fieldvalue = self.getvalue(op.args[1])
        if value.is_virtual():
            value.setfield(op.descr, fieldvalue)
        else:
            value.ensure_nonnull()
            self.heap_op_optimizer.optimize_SETFIELD_GC(op, value, fieldvalue)

    def optimize_NEW_WITH_VTABLE(self, op):
        self.make_virtual(op.args[0], op.result, op)

    def optimize_NEW(self, op):
        self.make_vstruct(op.descr, op.result, op)

    def optimize_NEW_ARRAY(self, op):
        sizebox = self.get_constant_box(op.args[0])
        if sizebox is not None:
            # if the original 'op' did not have a ConstInt as argument,
            # build a new one with the ConstInt argument
            if not isinstance(op.args[0], ConstInt):
                op = ResOperation(rop.NEW_ARRAY, [sizebox], op.result,
                                  descr=op.descr)
            self.make_varray(op.descr, sizebox.getint(), op.result, op)
        else:
            self.optimize_default(op)

    def optimize_ARRAYLEN_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            self.make_constant_int(op.result, value.getlength())
        else:
            value.ensure_nonnull()
            self.optimize_default(op)

    def optimize_GETARRAYITEM_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            indexbox = self.get_constant_box(op.args[1])
            if indexbox is not None:
                itemvalue = value.getitem(indexbox.getint())
                self.make_equal_to(op.result, itemvalue)
                return
        value.ensure_nonnull()
        self.heap_op_optimizer.optimize_GETARRAYITEM_GC(op, value)

    # note: the following line does not mean that the two operations are
    # completely equivalent, because GETARRAYITEM_GC_PURE is_always_pure().
    optimize_GETARRAYITEM_GC_PURE = optimize_GETARRAYITEM_GC

    def optimize_SETARRAYITEM_GC(self, op):
        value = self.getvalue(op.args[0])
        if value.is_virtual():
            indexbox = self.get_constant_box(op.args[1])
            if indexbox is not None:
                value.setitem(indexbox.getint(), self.getvalue(op.args[2]))
                return
        value.ensure_nonnull()
        fieldvalue = self.getvalue(op.args[2])
        self.heap_op_optimizer.optimize_SETARRAYITEM_GC(op, value, fieldvalue)

    def optimize_INSTANCEOF(self, op):
        value = self.getvalue(op.args[0])
        realclassbox = value.get_constant_class(self.cpu)
        if realclassbox is not None:
            checkclassbox = self.cpu.typedescr2classbox(op.descr)
            result = self.cpu.ts.subclassOf(self.cpu, realclassbox, 
                                                      checkclassbox)
            self.make_constant_int(op.result, result)
            return
        self.emit_operation(op)

    def optimize_DEBUG_MERGE_POINT(self, op):
        self.emit_operation(op)

    def optimize_CALL_LOOPINVARIANT(self, op):
        funcvalue = self.getvalue(op.args[0])
        if not funcvalue.is_constant():
            self.optimize_default(op)
            return
        resvalue = self.loop_invariant_results.get(op.args[0].getint(), None)
        if resvalue is not None:
            self.make_equal_to(op.result, resvalue)
            return
        # change the op to be a normal call, from the backend's point of view
        # there is no reason to have a separate operation for this
        op.opnum = rop.CALL
        self.optimize_default(op)
        resvalue = self.getvalue(op.result)
        self.loop_invariant_results[op.args[0].getint()] = resvalue
            

optimize_ops = _findall(Optimizer, 'optimize_')


class CachedArrayItems(object):
    def __init__(self):
        self.fixed_index_items = {}
        self.var_index_item = None
        self.var_index_indexvalue = None


class HeapOpOptimizer(object):
    def __init__(self, optimizer):
        self.optimizer = optimizer
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
            return self.optimizer.getvalue(op.args[1])
        return d.get(value, None)

    def cache_arrayitem_value(self, descr, value, indexvalue, fieldvalue, write=False):
        d = self.cached_arrayitems.get(descr, None)
        if d is None:
            d = self.cached_arrayitems[descr] = {}
        cache = d.get(value, None)
        if cache is None:
            cache = d[value] = CachedArrayItems()
        indexbox = self.optimizer.get_constant_box(indexvalue.box)
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
        indexbox = self.optimizer.get_constant_box(indexvalue.box)
        if indexbox is not None:
            return cache.fixed_index_items.get(indexbox.getint(), None)
        elif cache.var_index_indexvalue is indexvalue:
            return cache.var_index_item
        return None

    def emitting_operation(self, op):
        if op.has_no_side_effect():
            return
        if op.is_ovf():
            return
        if op.is_guard():
            return
        opnum = op.opnum
        if (opnum == rop.SETFIELD_GC or
            opnum == rop.SETARRAYITEM_GC or
            opnum == rop.DEBUG_MERGE_POINT):
            return
        if (opnum == rop.CALL or
            opnum == rop.CALL_MAY_FORCE or
            opnum == rop.CALL_ASSEMBLER):
            if opnum == rop.CALL_ASSEMBLER:
                effectinfo = None
            else:
                effectinfo = op.descr.get_extra_info()
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
                if effectinfo.forces_virtual_or_virtualizable:
                    vrefinfo = self.optimizer.metainterp_sd.virtualref_info
                    self.force_lazy_setfield(vrefinfo.descr_forced)
                    # ^^^ we only need to force this field; the other fields
                    # of virtualref_info and virtualizable_info are not gcptrs.
                return
            self.force_all_lazy_setfields()
        elif op.is_final() or (not we_are_translated() and
                               op.opnum < 0):   # escape() operations
            self.force_all_lazy_setfields()
        self.clean_caches()

    def force_lazy_setfield(self, descr, before_guard=False):
        try:
            op = self.lazy_setfields[descr]
        except KeyError:
            return
        del self.lazy_setfields[descr]
        self.optimizer._emit_operation(op)
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
            if ((prevop.is_comparison() or prevop.opnum == rop.CALL_MAY_FORCE)
                and prevop.result not in lastop.args):
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
            value = self.optimizer.getvalue(op.args[0])
            assert not value.is_virtual()      # it must be a non-virtual
            fieldvalue = self.optimizer.getvalue(op.args[1])
            if fieldvalue.is_virtual():
                # this is the case that we leave to resume.py
                pendingfields.append((descr, value.box,
                                      fieldvalue.get_key_box()))
            else:
                self.force_lazy_setfield(descr, before_guard=True)
        return pendingfields

    def force_lazy_setfield_if_necessary(self, op, value, write=False):
        try:
            op1 = self.lazy_setfields[op.descr]
        except KeyError:
            if write:
                self.lazy_setfields_descrs.append(op.descr)
        else:
            if self.optimizer.getvalue(op1.args[0]) is not value:
                self.force_lazy_setfield(op.descr)

    def optimize_GETFIELD_GC(self, op, value):
        self.force_lazy_setfield_if_necessary(op, value)
        # check if the field was read from another getfield_gc just before
        # or has been written to recently
        fieldvalue = self.read_cached_field(op.descr, value)
        if fieldvalue is not None:
            self.optimizer.make_equal_to(op.result, fieldvalue)
            return
        # default case: produce the operation
        value.ensure_nonnull()
        self.optimizer.optimize_default(op)
        # then remember the result of reading the field
        fieldvalue = self.optimizer.getvalue(op.result)
        self.cache_field_value(op.descr, value, fieldvalue)

    def optimize_SETFIELD_GC(self, op, value, fieldvalue):
        self.force_lazy_setfield_if_necessary(op, value, write=True)
        self.lazy_setfields[op.descr] = op
        # remember the result of future reads of the field
        self.cache_field_value(op.descr, value, fieldvalue, write=True)

    def optimize_GETARRAYITEM_GC(self, op, value):
        indexvalue = self.optimizer.getvalue(op.args[1])
        fieldvalue = self.read_cached_arrayitem(op.descr, value, indexvalue)
        if fieldvalue is not None:
            self.optimizer.make_equal_to(op.result, fieldvalue)
            return
        self.optimizer.optimize_default(op)
        fieldvalue = self.optimizer.getvalue(op.result)
        self.cache_arrayitem_value(op.descr, value, indexvalue, fieldvalue)

    def optimize_SETARRAYITEM_GC(self, op, value, fieldvalue):
        self.optimizer.emit_operation(op)
        indexvalue = self.optimizer.getvalue(op.args[1])
        self.cache_arrayitem_value(op.descr, value, indexvalue, fieldvalue,
                                   write=True)


