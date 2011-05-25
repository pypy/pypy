from pypy.jit.metainterp import resume
from pypy.jit.metainterp.optimizeopt import virtualize
from pypy.jit.metainterp.optimizeopt.optimizer import LEVEL_CONSTANT, \
                                                      LEVEL_KNOWNCLASS, \
                                                      LEVEL_NONNULL, \
                                                      LEVEL_UNKNOWN, \
                                                      MININT, MAXINT, OptValue
from pypy.jit.metainterp.history import BoxInt, ConstInt, BoxPtr, Const
from pypy.jit.metainterp.optimizeutil import InvalidLoop
from pypy.jit.metainterp.optimizeopt.intutils import IntBound
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rlib.objectmodel import we_are_translated

class AbstractVirtualStateInfo(resume.AbstractVirtualInfo):
    position = -1
    
    def generalization_of(self, other):
        raise NotImplementedError

    def generate_guards(self, other, box, cpu, extra_guards):
        if self.generalization_of(other):
            return
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
    
class AbstractVirtualStructStateInfo(AbstractVirtualStateInfo):
    def __init__(self, fielddescrs):
        self.fielddescrs = fielddescrs

    def generalization_of(self, other):
        assert self.position != -1
        if self.position != other.position:
            return False
        if not self._generalization_of(other):
            return False
        assert len(self.fielddescrs) == len(self.fieldstate)
        assert len(other.fielddescrs) == len(other.fieldstate)
        if len(self.fielddescrs) != len(other.fielddescrs):
            return False
        
        for i in range(len(self.fielddescrs)):
            if other.fielddescrs[i] is not self.fielddescrs[i]:
                return False
            if not self.fieldstate[i].generalization_of(other.fieldstate[i]):
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
        
class VArrayStateInfo(AbstractVirtualStateInfo):
    def __init__(self, arraydescr):
        self.arraydescr = arraydescr

    def generalization_of(self, other):
        assert self.position != -1
        if self.position != other.position:
            return False
        if self.arraydescr is not other.arraydescr:
            return False
        if len(self.fieldstate) != len(other.fieldstate):
            return False
        for i in range(len(self.fieldstate)):
            if not self.fieldstate[i].generalization_of(other.fieldstate[i]):
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
        
class NotVirtualStateInfo(AbstractVirtualStateInfo):
    def __init__(self, value):
        self.known_class = value.known_class
        self.level = value.level
        if value.intbound is None:
            self.intbound = IntBound(MININT, MAXINT)
        else:
            self.intbound = value.intbound.clone()
        if value.is_constant():
            self.constbox = value.box
        else:
            self.constbox = None
        self.position_in_notvirtuals = -1

    def generalization_of(self, other):
        # XXX This will always retrace instead of forcing anything which
        # might be what we want sometimes?
        assert self.position != -1
        if self.position != other.position:
            return False
        if not isinstance(other, NotVirtualStateInfo):
            return False
        if other.level < self.level:
            return False
        if self.level == LEVEL_CONSTANT:
            if not self.constbox.same_constant(other.constbox):
                return False
        elif self.level == LEVEL_KNOWNCLASS:
            if self.known_class != other.known_class: # FIXME: use issubclass?
                return False
        return self.intbound.contains_bound(other.intbound)

    def _generate_guards(self, other, box, cpu, extra_guards):
        if not isinstance(other, NotVirtualStateInfo):
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

class VirtualState(object):
    def __init__(self, state):
        self.state = state
        self.info_counter = -1
        self.notvirtuals = [] # FIXME: We dont need this list, only it's length
        for s in state:
            s.enum(self)

    def generalization_of(self, other):
        assert len(self.state) == len(other.state)
        for i in range(len(self.state)):
            if not self.state[i].generalization_of(other.state[i]):
                return False
        return True

    def generate_guards(self, other, args, cpu, extra_guards):        
        assert len(self.state) == len(other.state) == len(args)
        for i in range(len(self.state)):
            self.state[i].generate_guards(other.state[i], args[i],
                                          cpu, extra_guards)

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

