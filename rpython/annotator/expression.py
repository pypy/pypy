from rpython.flowspace.model import Variable
from rpython.flowspace.operation import op
from rpython.annotator.model import SomeType

class V_Type(Variable):
    def __init__(self, v_obj):
        Variable.__init__(self)
        self.arg = v_obj
        s = SomeType()
        s.is_type_of = [v_obj]
        self.annotation = s

    def as_operation(self):
        return op.type(self.arg)
