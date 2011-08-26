from pypy.jit.metainterp import resume
from pypy.jit.metainterp.optimizeopt import virtualize
from pypy.jit.metainterp.optimizeopt.optimizer import LEVEL_CONSTANT, \
                                                      LEVEL_KNOWNCLASS, \
                                                      LEVEL_NONNULL, \
                                                      LEVEL_UNKNOWN, \
                                                      MININT, MAXINT, OptValue
from pypy.jit.metainterp.history import BoxInt, ConstInt, BoxPtr, Const
from pypy.jit.metainterp.optimize import InvalidLoop
from pypy.jit.metainterp.optimizeopt.intutils import IntBound, IntUnbounded
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import debug_start, debug_stop, debug_print
from pypy.rlib.objectmodel import we_are_translated
import os

class AbstractVirtualStateInfo(resume.AbstractVirtualInfo):
    position = -1
    
    def generalization_of(self, other, renum, bad):
        raise NotImplementedError

    def generate_guards(self, other, box, cpu, extra_guards, renum):
        if self.generalization_of(other, renum, {}):
            return
        if renum[self.position] != other.position:
            raise InvalidLoop
        self._generate_guards(other, box, cpu, extra_guards)

    def _generate_guards(self, other, box, cpu, extra_guards):
        raise InvalidLoop

    def enum_forced_boxes(self, boxes, value):
        raise NotImplementedError

    def enum(self, virtual_state):
        if self.position != -1:
            return
        virtual_state.info_counter += 1
        self.position = virtual_state.info_counter
        self._enum(virtual_state)

    def _enum(self, virtual_state):
        raise NotImplementedError

    def debug_print(self, indent, seen, bad):
        mark = ''
        if self in bad:
            mark = '*'
        self.debug_header(indent + mark)
        if self not in seen:
            seen[self] = True
            for s in self.fieldstate:
                s.debug_print(indent + "    ", seen, bad)
        else:
            debug_print(indent + "    ...")
                

    def debug_header(self, indent):
        raise NotImplementedError


class AbstractVirtualStructStateInfo(AbstractVirtualStateInfo):
    def __init__(self, fielddescrs):
        self.fielddescrs = fielddescrs

    def generalization_of(self, other, renum, bad):
        assert self.position != -1
        if self.position in renum:
            if renum[self.position] == other.position:
                return True
            bad[self] = True
            bad[other] = True
            return False
        renum[self.position] = other.position
        if not self._generalization_of(other):
            bad[self] = True
            bad[other] = True
            return False
        assert len(self.fielddescrs) == len(self.fieldstate)
        assert len(other.fielddescrs) == len(other.fieldstate)
        if len(self.fielddescrs) != len(other.fielddescrs):
            bad[self] = True
            bad[other] = True
            return False
        
        for i in range(len(self.fielddescrs)):
            if other.fielddescrs[i] is not self.fielddescrs[i]:
                bad[self] = True
                bad[other] = True
                return False
            if not self.fieldstate[i].generalization_of(other.fieldstate[i],
                                                        renum, bad):
                bad[self] = True
                bad[other] = True
                return False

        return True

    def _generalization_of(self, other):
        raise NotImplementedError

    def enum_forced_boxes(self, boxes, value):
        assert isinstance(value, virtualize.AbstractVirtualStructValue)
        assert value.is_virtual()
        for i in range(len(self.fielddescrs)):
            v = value._fields[self.fielddescrs[i]]
            s = self.fieldstate[i]
            if s.position > self.position:
                s.enum_forced_boxes(boxes, v)

    def _enum(self, virtual_state):
        for s in self.fieldstate:
            s.enum(virtual_state)
        
        
class VirtualStateInfo(AbstractVirtualStructStateInfo):
    def __init__(self, known_class, fielddescrs):
        AbstractVirtualStructStateInfo.__init__(self, fielddescrs)
        self.known_class = known_class

    def _generalization_of(self, other):
        if not isinstance(other, VirtualStateInfo):
            return False
        if not self.known_class.same_constant(other.known_class):
            return False
        return True

    def debug_header(self, indent):
        debug_print(indent + 'VirtualStateInfo(%d):' % self.position)
        
class VStructStateInfo(AbstractVirtualStructStateInfo):
    def __init__(self, typedescr, fielddescrs):
        AbstractVirtualStructStateInfo.__init__(self, fielddescrs)
        self.typedescr = typedescr

    def _generalization_of(self, other):        
        if not isinstance(other, VStructStateInfo):
            return False
        if self.typedescr is not other.typedescr:
            return False
        return True

    def debug_header(self, indent):
        debug_print(indent + 'VStructStateInfo(%d):' % self.position)
        
class VArrayStateInfo(AbstractVirtualStateInfo):
    def __init__(self, arraydescr):
        self.arraydescr = arraydescr

    def generalization_of(self, other, renum, bad):
        assert self.position != -1
        if self.position in renum:
            if renum[self.position] == other.position:
                return True
            bad[self] = True
            bad[other] = True
            return False
        renum[self.position] = other.position
        if not isinstance(other, VArrayStateInfo):
            bad[self] = True
            bad[other] = True
            return False
        if self.arraydescr is not other.arraydescr:
            bad[self] = True
            bad[other] = True
            return False
        if len(self.fieldstate) != len(other.fieldstate):
            bad[self] = True
            bad[other] = True
            return False
        for i in range(len(self.fieldstate)):
            if not self.fieldstate[i].generalization_of(other.fieldstate[i],
                                                        renum, bad):
                bad[self] = True
                bad[other] = True
                return False
        return True

    def enum_forced_boxes(self, boxes, value):
        assert isinstance(value, virtualize.VArrayValue)
        assert value.is_virtual()
        for i in range(len(self.fieldstate)):
            v = value._items[i]
            s = self.fieldstate[i]
            if s.position > self.position:
                s.enum_forced_boxes(boxes, v)

    def _enum(self, virtual_state):
        for s in self.fieldstate:
            s.enum(virtual_state)

    def debug_header(self, indent):
        debug_print(indent + 'VArrayStateInfo(%d):' % self.position)
            
        
class NotVirtualStateInfo(AbstractVirtualStateInfo):
    def __init__(self, value):
        self.known_class = value.known_class
        self.level = value.level
        if value.intbound is None:
            self.intbound = IntUnbounded()
        else:
            self.intbound = value.intbound.clone()
        if value.is_constant():
            self.constbox = value.box
        else:
            self.constbox = None
        self.position_in_notvirtuals = -1
        self.lenbound = value.lenbound

    def generalization_of(self, other, renum, bad):
        # XXX This will always retrace instead of forcing anything which
        # might be what we want sometimes?
        assert self.position != -1
        if self.position in renum:
            if renum[self.position] == other.position:
                return True
            bad[self] = True
            bad[other] = True
            return False
        renum[self.position] = other.position
        if not isinstance(other, NotVirtualStateInfo):
            bad[self] = True
            bad[other] = True
            return False
        if other.level < self.level:
            bad[self] = True
            bad[other] = True
            return False
        if self.level == LEVEL_CONSTANT:
            if not self.constbox.same_constant(other.constbox):
                bad[self] = True
                bad[other] = True
                return False
        elif self.level == LEVEL_KNOWNCLASS:
            if not self.known_class.same_constant(other.known_class):
                bad[self] = True
                bad[other] = True
                return False
        if not self.intbound.contains_bound(other.intbound):
            bad[self] = True
            bad[other] = True
            return False
        if self.lenbound and other.lenbound:
            if self.lenbound.mode != other.lenbound.mode or \
               self.lenbound.descr != other.lenbound.descr or \
               not self.lenbound.bound.contains_bound(other.lenbound.bound):
                bad[self] = True
                bad[other] = True
                return False
        elif self.lenbound:
            bad[self] = True
            bad[other] = True
            return False
        return True

    def _generate_guards(self, other, box, cpu, extra_guards):
        if not isinstance(other, NotVirtualStateInfo):
            raise InvalidLoop

        if self.lenbound or other.lenbound:
            raise InvalidLoop

        if self.level == LEVEL_KNOWNCLASS and \
           box.nonnull() and \
           self.known_class.same_constant(cpu.ts.cls_of_box(box)):
            # Note: This is only a hint on what the class of box was
            # during the trace. There are actually no guarentees that this
            # box realy comes from a trace. The hint is used here to choose
            # between either eimtting a guard_class and jumping to an
            # excisting compiled loop or retracing the loop. Both
            # alternatives will always generate correct behaviour, but
            # performace will differ.
            op = ResOperation(rop.GUARD_NONNULL, [box], None)
            extra_guards.append(op)
            op = ResOperation(rop.GUARD_CLASS, [box, self.known_class], None)
            extra_guards.append(op)
            return
        
        if self.level == LEVEL_NONNULL and \
               other.level == LEVEL_UNKNOWN and \
               isinstance(box, BoxPtr) and \
               box.nonnull():
            op = ResOperation(rop.GUARD_NONNULL, [box], None)
            extra_guards.append(op)
            return
        
        if self.level == LEVEL_UNKNOWN and \
               other.level == LEVEL_UNKNOWN and \
               isinstance(box, BoxInt) and \
               self.intbound.contains(box.getint()):
            if self.intbound.has_lower:
                bound = self.intbound.lower
                if not (other.intbound.has_lower and \
                        other.intbound.lower >= bound):
                    res = BoxInt()
                    op = ResOperation(rop.INT_GE, [box, ConstInt(bound)], res)
                    extra_guards.append(op)
                    op = ResOperation(rop.GUARD_TRUE, [res], None)
                    extra_guards.append(op)
            if self.intbound.has_upper:
                bound = self.intbound.upper
                if not (other.intbound.has_upper and \
                        other.intbound.upper <= bound):
                    res = BoxInt()
                    op = ResOperation(rop.INT_LE, [box, ConstInt(bound)], res)
                    extra_guards.append(op)
                    op = ResOperation(rop.GUARD_TRUE, [res], None)
                    extra_guards.append(op)
            return
        
        # Remaining cases are probably not interesting
        raise InvalidLoop
        if self.level == LEVEL_CONSTANT:
            import pdb; pdb.set_trace()
            raise NotImplementedError

    def enum_forced_boxes(self, boxes, value):
        if self.level == LEVEL_CONSTANT:
            return
        assert 0 <= self.position_in_notvirtuals 
        boxes[self.position_in_notvirtuals] = value.force_box()

    def _enum(self, virtual_state):
        if self.level == LEVEL_CONSTANT:
            return
        self.position_in_notvirtuals = len(virtual_state.notvirtuals)
        virtual_state.notvirtuals.append(self)

    def debug_print(self, indent, seen, bad):
        mark = ''
        if self in bad:
            mark = '*'
        if we_are_translated():
            l = {LEVEL_UNKNOWN: 'Unknown',
                 LEVEL_NONNULL: 'NonNull',
                 LEVEL_KNOWNCLASS: 'KnownClass',
                 LEVEL_CONSTANT: 'Constant',
                 }[self.level]
        else:
            l = {LEVEL_UNKNOWN: 'Unknown',
                 LEVEL_NONNULL: 'NonNull',
                 LEVEL_KNOWNCLASS: 'KnownClass(%r)' % self.known_class,
                 LEVEL_CONSTANT: 'Constant(%r)' % self.constbox,
                 }[self.level]

        lb = ''
        if self.lenbound:
            lb = ', ' + self.lenbound.bound.__repr__()
        
        debug_print(indent + mark + 'NotVirtualInfo(%d' % self.position +
                    ', ' + l + ', ' + self.intbound.__repr__() + lb + ')')

class VirtualState(object):
    def __init__(self, state):
        self.state = state
        self.info_counter = -1
        self.notvirtuals = [] # FIXME: We dont need this list, only it's length
        for s in state:
            s.enum(self)

    def generalization_of(self, other, bad=None):
        if bad is None:
            bad = {}
        assert len(self.state) == len(other.state)
        renum = {}
        for i in range(len(self.state)):
            if not self.state[i].generalization_of(other.state[i], renum, bad):
                return False
        return True

    def generate_guards(self, other, args, cpu, extra_guards):        
        assert len(self.state) == len(other.state) == len(args)
        renum = {}
        for i in range(len(self.state)):
            self.state[i].generate_guards(other.state[i], args[i],
                                          cpu, extra_guards, renum)

    def make_inputargs(self, values, keyboxes=False):
        assert len(values) == len(self.state)
        inputargs = [None] * len(self.notvirtuals)
        for i in range(len(values)):
            self.state[i].enum_forced_boxes(inputargs, values[i])

        if keyboxes:
            for i in range(len(values)):
                if not isinstance(self.state[i], NotVirtualStateInfo):
                    box = values[i].get_key_box()
                    assert not isinstance(box, Const)
                    inputargs.append(box)

        assert None not in inputargs
            
        return inputargs

    def debug_print(self, hdr='', bad=None):
        if bad is None:
            bad = {}
        debug_print(hdr + "VirtualState():")
        seen = {}
        for s in self.state:
            s.debug_print("    ", seen, bad)

class VirtualStateAdder(resume.ResumeDataVirtualAdder):
    def __init__(self, optimizer):
        self.fieldboxes = {}
        self.optimizer = optimizer
        self.info = {}

    def register_virtual_fields(self, keybox, fieldboxes):
        self.fieldboxes[keybox] = fieldboxes
        
    def already_seen_virtual(self, keybox):
        return keybox in self.fieldboxes

    def getvalue(self, box):
        return self.optimizer.getvalue(box)

    def state(self, box):
        value = self.getvalue(box)
        box = value.get_key_box()
        try:
            info = self.info[box]
        except KeyError:
            if value.is_virtual():
                self.info[box] = info = value.make_virtual_info(self, None)
                flds = self.fieldboxes[box]
                info.fieldstate = [self.state(b) for b in flds]
            else:
                self.info[box] = info = self.make_not_virtual(value)
        return info

    def get_virtual_state(self, jump_args):
        self.optimizer.force_at_end_of_preamble()
        already_forced = {}
        values = [self.getvalue(box).force_at_end_of_preamble(already_forced)
                  for box in jump_args]

        for value in values:
            if value.is_virtual():
                value.get_args_for_fail(self)
            else:
                self.make_not_virtual(value)
        return VirtualState([self.state(box) for box in jump_args])

    def make_not_virtual(self, value):
        return NotVirtualStateInfo(value)

    def make_virtual(self, known_class, fielddescrs):
        return VirtualStateInfo(known_class, fielddescrs)

    def make_vstruct(self, typedescr, fielddescrs):
        return VStructStateInfo(typedescr, fielddescrs)

    def make_varray(self, arraydescr):
        return VArrayStateInfo(arraydescr)

class BoxNotProducable(Exception):
    pass

class ShortBoxes(object):
    def __init__(self, optimizer, surviving_boxes):
        self.potential_ops = {}
        self.duplicates = {}
        self.aliases = {}
        self.optimizer = optimizer
        for box in surviving_boxes:
            self.potential_ops[box] = None
        optimizer.produce_potential_short_preamble_ops(self)

        self.short_boxes = {}

        for box in self.potential_ops.keys():
            try:
                self.produce_short_preamble_box(box)
            except BoxNotProducable:
                pass
        self.duplicate_short_boxes_if_needed()

    def produce_short_preamble_box(self, box):
        if box in self.short_boxes:
            return 
        if isinstance(box, Const):
            return 
        if box in self.potential_ops:
            op = self.potential_ops[box]
            if op:
                for arg in op.getarglist():
                    self.produce_short_preamble_box(arg)
            self.short_boxes[box] = op
        else:
            raise BoxNotProducable

    def add_potential(self, op):
        if op.result not in self.potential_ops:
            self.potential_ops[op.result] = op
            return op
        return self.duplicate(self.potential_ops, op)

    def duplicate(self, destination, op):
        newop = op.clone()
        newop.result = op.result.clonebox()
        destination[newop.result] = newop
        if op.result in self.duplicates:
            self.duplicates[op.result].append(newop.result)
        else:
            self.duplicates[op.result] = [newop.result]
        self.optimizer.make_equal_to(newop.result, self.optimizer.getvalue(op.result))
        return newop

    def duplicate_short_boxes_if_needed(self):
        if os.environ.get('DONT_DUPLICATE'):
            return
        may_need_duplication = {}
        for op in self.short_boxes.values():
            if op:
                may_need_duplication[op] = True
        while may_need_duplication:
            op, _ = may_need_duplication.popitem()
            self.maybe_duplicate_op(op, may_need_duplication)

    def maybe_duplicate_op(self, op, may_need_duplication):
        for arg in op.getarglist():
            if arg in self.short_boxes:
                producer = self.producer(arg)
                if producer in may_need_duplication:
                    del may_need_duplication[producer]
                    self.maybe_duplicate_op(producer, may_need_duplication)
        for i in range(len(op.getarglist())):
            arg = op.getarg(i)
            if arg in self.duplicates:
                for box in self.duplicates[arg]:
                    if box in self.short_boxes:
                        newop = self.duplicate(self.short_boxes, op)
                        newop.setarg(i, box)
            # XXX If more than one arg is duplicated this does not give
            #     all combinations as each argument is treated separately

    def debug_print(self, logops):
        debug_start('jit-short-boxes')
        for box, op in self.short_boxes.items():
            if op:
                debug_print(logops.repr_of_arg(box) + ': ' + logops.repr_of_resop(op))
            else:
                debug_print(logops.repr_of_arg(box) + ': None')
        debug_stop('jit-short-boxes')
        
    def operations(self):
        if not we_are_translated(): # For tests
            ops = self.short_boxes.values()
            ops.sort(key=str, reverse=True)
            return ops
        return self.short_boxes.values()

    def producer(self, box):
        return self.short_boxes[box]

    def has_producer(self, box):
        return box in self.short_boxes

    def alias(self, newbox, oldbox):
        if not isinstance(oldbox, Const) and newbox not in self.short_boxes:
            self.short_boxes[newbox] = self.short_boxes[oldbox]
        self.aliases[newbox] = oldbox
        
    def original(self, box):
        while box in self.aliases:
            box = self.aliases[box]
        return box
