from rpython.flowspace.model import Variable

class V_Type(Variable):
    def __init__(self, v_obj):
        from rpython.annotator.model import SomeType
        Variable.__init__(self)
        self.arg = v_obj
        s = SomeType()
        s.is_type_of = [v_obj]
        self.annotation = s

    def as_operation(self):
        from rpython.flowspace.operation import op
        return op.type(self.arg)

    def __eq__(self, other):
        return isinstance(other, V_Type) and other.arg == self.arg

    def __hash__(self):
        return hash((type(self), self.arg))

    def __repr__(self):
        return 'type(%s)' % self.arg

    def replace(self, mapping):
        if self.arg in mapping:
            return V_Type(mapping[self.arg])
        else:
            return self

    @property
    def dependencies(self):
        return self.arg.dependencies
