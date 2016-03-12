from rpython.jit.metainterp.history import newconst

class CompatibilityCondition(object):
    """ A collections of conditions that an object needs to fulfil. """
    def __init__(self, ptr):
        self.known_valid = ptr
        self.pure_call_conditions = []

    def record_pure_call(self, op, res):
        self.pure_call_conditions.append((op, res))
