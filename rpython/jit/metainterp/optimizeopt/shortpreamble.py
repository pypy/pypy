
from rpython.jit.metainterp.resoperation import rop, ResOperation
from rpython.jit.metainterp.history import Const

class BoxNotProducable(Exception):
    pass


class ShortBoxes(object):
    def __init__(self):
        self.potential_ops = {}
        self.inputarg_boxes = {}
        self.synthetic = {}
        self.alternatives = {}
        self.extra_same_as = []

    def create_short_boxes(self, optimizer, inputargs):
        for box in inputargs:
            self.inputarg_boxes[box] = None
        optimizer.produce_potential_short_preamble_ops(self)

        self.short_boxes = {}
        self.short_boxes_in_production = {}

        for op in self.potential_ops.keys():
            try:
                self.produce_short_preamble_op(op)
            except BoxNotProducable:
                pass

        self.short_boxes_in_production = None # Not needed anymore

    def prioritized_alternatives(self, box):
        if box not in self.alternatives:
            return [self.potential_ops[box]]
        alts = self.alternatives[box]
        hi, lo = 0, len(alts) - 1
        while hi < lo:
            if alts[lo] is None: # Inputarg, lowest priority
                alts[lo], alts[-1] = alts[-1], alts[lo]
                lo -= 1
            elif alts[lo] not in self.synthetic: # Hi priority
                alts[hi], alts[lo] = alts[lo], alts[hi]
                hi += 1
            else: # Low priority
                lo -= 1
        return alts

    def add_to_short(self, op):
        if op in self.short_boxes:
            xxx
            #if op is None:
            #    xxx
            #    oldop = self.short_boxes[box]
            #    self.rename[op] = oldop
            #    self.short_boxes[box] = None
            #    self.short_boxes[oldop] = oldop
            #else:
            #    xxxx
            #    newop = op.clone()
            #    newbox = newop.result = op.result.clonebox()
            #    self.short_boxes[newop.result] = newop
            #xxx
            #value = self.optimizer.getvalue(box)
            #self.optimizer.emit_operation(ResOperation(rop.SAME_AS, [box], newbox))
            #self.optimizer.make_equal_to(newbox, value)
            #if op is None:
            #    if self.short_boxes[box] is not box:
            #        xxx
            #else:
            #    if self.short_boxes[box] is not op:
            #        if self.short_boxes[box] is None:
            #            self.short_boxes[box] = op
            #        else:
            #            xxx
        else:
            self.short_boxes[op] = None

    def produce_short_preamble_op(self, op):
        if op in self.short_boxes:
            return
        if op in self.inputarg_boxes:
            return
        if isinstance(op, Const):
            return
        if op in self.short_boxes_in_production:
            raise BoxNotProducable
        self.short_boxes_in_production[op] = None

        if op in self.potential_ops:
            ops = self.prioritized_alternatives(op)
            produced_one = False
            for newop in ops:
                try:
                    if newop:
                        for arg in newop.getarglist():
                            self.produce_short_preamble_op(arg)
                except BoxNotProducable:
                    pass
                else:
                    produced_one = True
                    self.add_to_short(newop)
            if not produced_one:
                raise BoxNotProducable
        else:
            raise BoxNotProducable

    def add_potential(self, op, result=None, synthetic=False):
        if result is None:
            result = op
        if result in self.potential_ops:
            if result not in self.alternatives:
                self.alternatives[result] = [self.potential_ops[result]]
            self.alternatives[result].append(op)
        else:
            self.potential_ops[result] = op
        if synthetic:
            self.synthetic[result] = True
