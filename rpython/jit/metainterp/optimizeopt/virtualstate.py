from rpython.jit.metainterp.walkvirtual import VirtualVisitor
from rpython.jit.metainterp.history import (ConstInt, Const,
        ConstPtr, ConstFloat)
from rpython.jit.metainterp.optimizeopt import info
from rpython.jit.metainterp.optimizeopt.intutils import IntUnbounded
from rpython.jit.metainterp.resoperation import rop, ResOperation,\
     AbstractInputArg
from rpython.rlib.debug import debug_start, debug_stop, debug_print
from rpython.rlib.objectmodel import we_are_translated

LEVEL_UNKNOWN = '\x00'
LEVEL_NONNULL = '\x01'
LEVEL_KNOWNCLASS = '\x02'
LEVEL_CONSTANT = '\x03'

class BadVirtualState(Exception):
    pass

class VirtualStatesCantMatch(Exception):
    def __init__(self, msg='?', state=None):
        self.msg = msg
        self.state = state

class GenerateGuardState(object):
    def __init__(self, cpu=None, guards=None, renum=None, bad=None):
        self.cpu = cpu
        if guards is None:
            guards = []
        self.extra_guards = guards
        if renum is None:
            renum = {}
        self.renum = renum
        if bad is None:
            bad = {}
        self.bad = bad

class AbstractVirtualStateInfo(object):
    position = -1

    def generate_guards(self, other, op, opinfo, state):
        """ generate guards (output in the list extra_guards) that make runtime
        values of the shape other match the shape of self. if that's not
        possible, VirtualStatesCantMatch is thrown and bad gets keys set which
        parts of the state are the problem.

        the function can peek into opinfo (and particularly also the op)
        as a guiding heuristic whether making such guards makes
        sense. if None is passed in for op, no guard is ever generated, and
        this function degenerates to a generalization check."""
        assert opinfo is None or isinstance(opinfo, info.AbstractInfo)
        assert self.position != -1
        if self.position in state.renum:
            if state.renum[self.position] != other.position:
                state.bad[self] = state.bad[other] = None
                raise VirtualStatesCantMatch(
                        'The numbering of the virtual states does not ' +
                        'match. This means that two virtual fields ' +
                        'have been set to the same Box in one of the ' +
                        'virtual states but not in the other.',
                        state)
        else:
            state.renum[self.position] = other.position
            try:
                self._generate_guards(other, op, opinfo, state)
            except VirtualStatesCantMatch, e:
                state.bad[self] = state.bad[other] = None
                if e.state is None:
                    e.state = state
                raise e

    def _generate_guards(self, other, value, state):
        raise VirtualStatesCantMatch(
                'Generating guards for making the VirtualStates ' +
                'at hand match have not been implemented')

    def enum_forced_boxes(self, boxes, value, optimizer):
        raise NotImplementedError

    def enum(self, virtual_state):
        if self.position != -1:
            return
        virtual_state.info_counter += 1
        self.position = virtual_state.info_counter
        self._enum(virtual_state)

    def _enum(self, virtual_state):
        raise NotImplementedError

    def debug_print(self, indent, seen, bad, metainterp_sd):
        mark = ''
        if self in bad:
            mark = '*'
        self.debug_header(indent + mark)
        if self not in seen:
            seen[self] = True
            for s in self.fieldstate:
                s.debug_print(indent + "    ", seen, bad, metainterp_sd)
        else:
            debug_print(indent + "    ...")

    def debug_header(self, indent):
        raise NotImplementedError


class AbstractVirtualStructStateInfo(AbstractVirtualStateInfo):
    def __init__(self, fielddescrs):
        self.fielddescrs = fielddescrs

    def _generate_guards(self, other, box, opinfo, state):
        if not self._generalization_of_structpart(other):
            raise VirtualStatesCantMatch("different kinds of structs")

        assert isinstance(other, AbstractVirtualStructStateInfo)
        assert len(self.fielddescrs) == len(self.fieldstate)
        assert len(other.fielddescrs) == len(other.fieldstate)
        if box is not None:
            yyy
            assert isinstance(value, virtualize.AbstractVirtualStructValue)
            assert value.is_virtual()

        if len(self.fielddescrs) != len(other.fielddescrs):
            raise VirtualStatesCantMatch("field descrs don't match")

        for i in range(len(self.fielddescrs)):
            if other.fielddescrs[i] is not self.fielddescrs[i]:
                raise VirtualStatesCantMatch("field descrs don't match")
            if box is not None:
                fieldbox = opinfo._fields[self.fielddescrs[i].get_index()]
                # must be there
                fieldinfo = fieldbox.get_forwarded()
            else:
                fieldbox = None
                fieldinfo = None
            self.fieldstate[i].generate_guards(other.fieldstate[i], fieldbox,
                                               fieldinfo, state)


    def _generalization_of_structpart(self, other):
        raise NotImplementedError

    def enum_forced_boxes(self, boxes, box, optimizer, force_boxes=False):
        box = optimizer.get_box_replacement(box)
        info = optimizer.getptrinfo(box)
        if info is None or not info.is_virtual():
            raise BadVirtualState()
        for i in range(len(self.fielddescrs)):
            state = self.fieldstate[i]
            if not state:
                continue
            if state.position > self.position:
                fieldbox = info._fields[i]
                state.enum_forced_boxes(boxes, fieldbox, optimizer, force_boxes)

    def _enum(self, virtual_state):
        for s in self.fieldstate:
            if s:
                s.enum(virtual_state)


class VirtualStateInfo(AbstractVirtualStructStateInfo):
    def is_virtual(self):
        return True

    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructStateInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    def _generalization_of_structpart(self, other):
        return (isinstance(other, VirtualStateInfo) and
                self.known_class.same_constant(other.known_class))


    def debug_header(self, indent):
        debug_print(indent + 'VirtualStateInfo(%d):' % self.position)


class VStructStateInfo(AbstractVirtualStructStateInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructStateInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    def _generalization_of_structpart(self, other):
        return (isinstance(other, VStructStateInfo) and
                self.typedescr is other.typedescr)

    def debug_header(self, indent):
        debug_print(indent + 'VStructStateInfo(%d):' % self.position)


class VArrayStateInfo(AbstractVirtualStateInfo):

    def __init__(self, arraydescr):
        self.arraydescr = arraydescr

    def _generate_guards(self, other, box, opinfo, state):
        if not isinstance(other, VArrayStateInfo):
            raise VirtualStatesCantMatch("other is not an array")
        if self.arraydescr is not other.arraydescr:
            raise VirtualStatesCantMatch("other is a different kind of array")
        if len(self.fieldstate) != len(other.fieldstate):
            raise VirtualStatesCantMatch("other has a different length")
        fieldbox = None
        fieldinfo = None
        for i in range(len(self.fieldstate)):
            if box is not None:
                assert isinstance(opinfo, info.ArrayPtrInfo)
                fieldbox = opinfo._items[i]
                fieldinfo = fieldbox.get_forwarded()
            self.fieldstate[i].generate_guards(other.fieldstate[i],
                                            fieldbox, fieldinfo, state)

    def enum_forced_boxes(self, boxes, box, optimizer, force_boxes=False):
        box = optimizer.get_box_replacement(box)
        info = optimizer.getptrinfo(box)
        if info is None or not info.is_virtual():
            raise BadVirtualState()
        if len(self.fieldstate) > info.getlength():
            raise BadVirtualState
        for i in range(len(self.fieldstate)):
            fieldbox = info.getitem(i)
            if fieldbox is None:
                xxx
                v = value.get_missing_null_value()
            s = self.fieldstate[i]
            if s.position > self.position:
                s.enum_forced_boxes(boxes, fieldbox, optimizer, force_boxes)

    def _enum(self, virtual_state):
        for s in self.fieldstate:
            s.enum(virtual_state)

    def debug_header(self, indent):
        debug_print(indent + 'VArrayStateInfo(%d):' % self.position)


class VArrayStructStateInfo(AbstractVirtualStateInfo):
    def __init__(self, arraydescr, fielddescrs):
        self.arraydescr = arraydescr
        self.fielddescrs = fielddescrs

    def _generate_guards(self, other, box, opinfo, state):
        if not isinstance(other, VArrayStructStateInfo):
            raise VirtualStatesCantMatch("other is not an VArrayStructStateInfo")
        if self.arraydescr is not other.arraydescr:
            raise VirtualStatesCantMatch("other is a different kind of array")

        if len(self.fielddescrs) != len(other.fielddescrs):
            raise VirtualStatesCantMatch("other has a different length")

        p = 0
        fieldbox = None
        fieldinfo = None
        for i in range(len(self.fielddescrs)):
            if len(self.fielddescrs[i]) != len(other.fielddescrs[i]):
                raise VirtualStatesCantMatch("other has a different length")
            for j in range(len(self.fielddescrs[i])):
                descr = self.fielddescrs[i][j]
                if descr is not other.fielddescrs[i][j]:
                    raise VirtualStatesCantMatch("other is a different kind of array")
                if box is not None:
                    xxx
                    assert isinstance(value, virtualize.VArrayStructValue)
                    v = value._items[i][descr]
                self.fieldstate[p].generate_guards(other.fieldstate[p],
                                                   fieldbox, fieldinfo,
                                                   state)
                p += 1

    def _enum(self, virtual_state):
        for s in self.fieldstate:
            s.enum(virtual_state)

    def enum_forced_boxes(self, boxes, value, optimizer):
        xxx
        if not isinstance(value, virtualize.VArrayStructValue):
            raise BadVirtualState
        if not value.is_virtual():
            raise BadVirtualState
        if len(self.fielddescrs) > len(value._items):
            raise BadVirtualState
        p = 0
        for i in range(len(self.fielddescrs)):
            for j in range(len(self.fielddescrs[i])):
                try:
                    v = value._items[i][self.fielddescrs[i][j]]
                except KeyError:
                    raise BadVirtualState
                s = self.fieldstate[p]
                if s.position > self.position:
                    s.enum_forced_boxes(boxes, v, optimizer)
                p += 1

    def debug_header(self, indent):
        debug_print(indent + 'VArrayStructStateInfo(%d):' % self.position)

class NotVirtualStateInfo(AbstractVirtualStateInfo):
    lenbound = None
    intbound = None
    level = LEVEL_UNKNOWN
    constbox = None
    known_class = None
    
    def __init__(self, cpu, type, info, is_opaque=False):
        self.is_opaque = is_opaque
        if info and info.is_constant():
            self.level = LEVEL_CONSTANT
            self.constbox = info.getconst()
            if type == 'r':
                self.known_class = info.get_known_class(cpu)
        elif type == 'r':
            if info:
                self.known_class = info.get_known_class(cpu)
                if self.known_class:
                    self.level = LEVEL_KNOWNCLASS
                elif info.is_nonnull():
                    self.level = LEVEL_NONNULL
                self.lenbound = info.getlenbound()
        elif type == 'i':
            self.intbound = info

    def is_const(self):
        return self.constbox is not None

    def is_virtual(self):
        return False

    def _generate_guards(self, other, box, opinfo, state):
        if self.is_opaque:
            box = None # generating guards for opaque pointers isn't safe
        # XXX This will always retrace instead of forcing anything which
        # might be what we want sometimes?
        if not isinstance(other, NotVirtualStateInfo):
            raise VirtualStatesCantMatch(
                    'The VirtualStates does not match as a ' +
                    'virtual appears where a pointer is needed ' +
                    'and it is too late to force it.')


        extra_guards = state.extra_guards
        cpu = state.cpu
        if self.lenbound and not self.lenbound.generalization_of(other.lenbound):
            raise VirtualStatesCantMatch("length bound does not match")

        if self.level == LEVEL_UNKNOWN:
            # confusingly enough, this is done also for pointers
            # which have the full range as the "bound", so it always works
            return self._generate_guards_intbounds(other, box, extra_guards)

        # the following conditions often peek into the runtime value that the
        # box had when tracing. This value is only used as an educated guess.
        # It is used here to choose between either emitting a guard and jumping
        # to an existing compiled loop or retracing the loop. Both alternatives
        # will always generate correct behaviour, but performance will differ.
        elif self.level == LEVEL_NONNULL:
            if other.level == LEVEL_UNKNOWN:
                if box is not None and box.nonnull():
                    op = ResOperation(rop.GUARD_NONNULL, [box], None)
                    extra_guards.append(op)
                    return
                else:
                    raise VirtualStatesCantMatch("other not known to be nonnull")
            elif other.level == LEVEL_NONNULL:
                return
            elif other.level == LEVEL_KNOWNCLASS:
                return # implies nonnull
            else:
                assert other.level == LEVEL_CONSTANT
                assert other.constbox
                if not other.constbox.nonnull():
                    raise VirtualStatesCantMatch("constant is null")
                return

        elif self.level == LEVEL_KNOWNCLASS:
            if other.level == LEVEL_UNKNOWN:
                if (box and box.nonnull() and
                        self.known_class.same_constant(cpu.ts.cls_of_box(box))):
                    op = ResOperation(rop.GUARD_NONNULL_CLASS, [box, self.known_class], None)
                    extra_guards.append(op)
                    return
                else:
                    raise VirtualStatesCantMatch("other's class is unknown")
            elif other.level == LEVEL_NONNULL:
                if box and self.known_class.same_constant(cpu.ts.cls_of_box(box)):
                    op = ResOperation(rop.GUARD_CLASS, [box, self.known_class], None)
                    extra_guards.append(op)
                    return
                else:
                    raise VirtualStatesCantMatch("other's class is unknown")
            elif other.level == LEVEL_KNOWNCLASS:
                if self.known_class.same_constant(other.known_class):
                    return
                raise VirtualStatesCantMatch("classes don't match")
            else:
                assert other.level == LEVEL_CONSTANT
                if (other.constbox.nonnull() and
                        self.known_class.same_constant(cpu.ts.cls_of_box(other.constbox))):
                    return
                else:
                    raise VirtualStatesCantMatch("classes don't match")

        else:
            assert self.level == LEVEL_CONSTANT
            if other.level == LEVEL_CONSTANT:
                if self.constbox.same_constant(other.constbox):
                    return
                raise VirtualStatesCantMatch("different constants")
            if box is not None and self.constbox.same_constant(box.constbox()):
                op = ResOperation(rop.GUARD_VALUE, [box, self.constbox], None)
                extra_guards.append(op)
                return
            else:
                raise VirtualStatesCantMatch("other not constant")
        assert 0, "unreachable"

    def _generate_guards_intbounds(self, other, boxinfo, extra_guards):
        if self.intbound is None:
            return
        if self.intbound.contains_bound(other.intbound):
            return
        if (boxinfo is not None and isinstance(box, BoxInt) and
                self.intbound.contains(box.getint())):
            # this may generate a few more guards than needed, but they are
            # optimized away when emitting them
            self.intbound.make_guards(box, extra_guards)
            return
        raise VirtualStatesCantMatch("intbounds don't match")

    def enum_forced_boxes(self, boxes, box, optimizer, force_boxes=False):
        if self.level == LEVEL_CONSTANT:
            return
        assert 0 <= self.position_in_notvirtuals
        if optimizer is not None:
            box = optimizer.get_box_replacement(box)
            if box.type == 'r':
                info = optimizer.getptrinfo(box)
                if info and info.is_virtual():
                    if force_boxes:
                        info.force_box(box, optimizer)
                    else:
                        raise BadVirtualState
        boxes[self.position_in_notvirtuals] = box

    def _enum(self, virtual_state):
        if self.level == LEVEL_CONSTANT:
            return
        self.position_in_notvirtuals = virtual_state.numnotvirtuals
        virtual_state.numnotvirtuals += 1

    def debug_print(self, indent, seen, bad, metainterp_sd=None):
        mark = ''
        if self in bad:
            mark = '*'
        if self.level == LEVEL_UNKNOWN:
            l = "Unknown"
        elif self.level == LEVEL_NONNULL:
            l = "NonNull"
        elif self.level == LEVEL_KNOWNCLASS:
            addr = self.known_class.getaddr()
            if metainterp_sd:
                name = metainterp_sd.get_name_from_address(addr)
            else:
                name = "?"
            l = "KnownClass(%s)" % name
        else:
            assert self.level == LEVEL_CONSTANT
            const = self.constbox
            if isinstance(const, ConstInt):
                l = "ConstInt(%s)" % (const.value, )
            elif isinstance(const, ConstPtr):
                if const.value:
                    l = "ConstPtr"
                else:
                    l = "ConstPtr(null)"
            else:
                assert isinstance(const, ConstFloat)
                l = "ConstFloat(%s)" % const.getfloat()

        lb = ''
        if self.lenbound:
            lb = ', ' + self.lenbound.bound.__repr__()

        debug_print(indent + mark + 'NotVirtualInfo(%d' % self.position +
                    ', ' + l + ', ' + self.intbound.__repr__() + lb + ')')


class VirtualState(object):
    def __init__(self, state):
        self.state = state
        self.info_counter = -1
        self.numnotvirtuals = 0
        for s in state:
            if s:
                s.enum(self)

    def generalization_of(self, other, bad=None, cpu=None):
        state = GenerateGuardState(cpu=cpu, bad=bad)
        assert len(self.state) == len(other.state)
        try:
            for i in range(len(self.state)):
                self.state[i].generate_guards(other.state[i], None, None, state)
        except VirtualStatesCantMatch:
            return False
        return True

    def generate_guards(self, other, values, cpu):
        assert len(self.state) == len(other.state) == len(values)
        state = GenerateGuardState(cpu)
        for i in range(len(self.state)):
            self.state[i].generate_guards(other.state[i], values[i],
                                          state)
        return state

    def make_inputargs(self, inputargs, optimizer, force_boxes=False,
                       append_virtuals=False):
        assert len(inputargs) == len(self.state)
        boxes = [None] * self.numnotvirtuals

        # We try twice. The first time around we allow boxes to be forced
        # which might change the virtual state if the box appear in more
        # than one place among the inputargs.
        if force_boxes:
            for i in range(len(inputargs)):
                self.state[i].enum_forced_boxes(boxes, inputargs[i], optimizer,
                                                True)
        for i in range(len(inputargs)):
            self.state[i].enum_forced_boxes(boxes, inputargs[i], optimizer)

        if append_virtuals:
            # we append the virtuals here in case some stuff is proven
            # to be not a virtual and there are getfields in the short preamble
            # that will read items out of there
            for i in range(len(inputargs)):
                if not isinstance(self.state[i], NotVirtualStateInfo):
                    boxes.append(inputargs[i])
            
        return boxes

    def debug_print(self, hdr='', bad=None, metainterp_sd=None):
        if bad is None:
            bad = {}
        debug_print(hdr + "VirtualState():")
        seen = {}
        for s in self.state:
            s.debug_print("    ", seen, bad, metainterp_sd)


class VirtualStateConstructor(VirtualVisitor):

    def __init__(self, optimizer):
        self.fieldboxes = {}
        self.optimizer = optimizer
        self.info = {}

    def register_virtual_fields(self, keybox, fieldboxes):
        self.fieldboxes[keybox] = fieldboxes

    def already_seen_virtual(self, keybox):
        return keybox in self.fieldboxes

    #def state(self, box):
    #    xxx
    #    value = self.getvalue(box)
    #    box = value.get_key_box()
    #    try:
    #        info = self.info[box]
    #    except KeyError:
    #        self.info[box] = info = value.visitor_dispatch_virtual_type(self)
    #        if value.is_virtual():
    #            flds = self.fieldboxes[box]
    #            info.fieldstate = [self.state_or_none(b, value) for b in flds]
    #    return info

    #def state_or_none(self, box, value):
    #    if box is None:
    #        box = value.get_missing_null_value().box
    #    return self.state(box)

    def create_state_or_none(self, box, opt):
        if box is None:
            return None
        return self.create_state(box, opt)

    def create_state(self, box, opt):
        box = opt.get_box_replacement(box)
        try:
            return self.info[box]
        except KeyError:
            pass
        if box.type == 'r':
            info = opt.getptrinfo(box)
            if info is not None and info.is_virtual():
                result = info.visitor_dispatch_virtual_type(self)
                self.info[box] = result
                info.visitor_walk_recursive(box, self, opt)
                result.fieldstate = [self.create_state_or_none(b, opt)
                                     for b in self.fieldboxes[box]]
            else:
                result = self.visit_not_virtual(box)
                self.info[box] = result
        elif box.type == 'i' or box.type == 'f':
            result = self.visit_not_virtual(box)
            self.info[box] = result
        else:
            assert False
        return result

    def get_virtual_state(self, jump_args):
        self.optimizer.force_at_end_of_preamble()
        if self.optimizer.optearlyforce:
            opt = self.optimizer.optearlyforce
        else:
            opt = self.optimizer
        state = []
        self.info = {}
        for box in jump_args:
            state.append(self.create_state(box, opt))
        return VirtualState(state)

    def visit_not_virtual(self, box):
        is_opaque = box in self.optimizer.opaque_pointers
        return NotVirtualStateInfo(self.optimizer.cpu, box.type,
                                   self.optimizer.getinfo(box))

    def visit_virtual(self, known_class, fielddescrs):
        return VirtualStateInfo(known_class, fielddescrs)

    def visit_vstruct(self, typedescr, fielddescrs):
        return VStructStateInfo(typedescr, fielddescrs)

    def visit_varray(self, arraydescr, clear):
        # 'clear' is ignored here.  I *think* it is correct, because so
        # far in force_at_end_of_preamble() we force all array values
        # to be non-None, so clearing is not important any more
        return VArrayStateInfo(arraydescr)

    def visit_varraystruct(self, arraydescr, fielddescrs):
        return VArrayStructStateInfo(arraydescr, fielddescrs)

