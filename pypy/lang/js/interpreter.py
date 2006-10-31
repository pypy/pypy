
from pypy.lang.js.astgen import *
from pypy.lang.js.context import ExecutionContext
from pypy.lang.js.jsobj import W_Number, W_String

def writer(x):
    print x

class __extend__(Assign):
    def call(self, context):
        val = self.expr.call(context)
        context.assign(self.identifier.name, val)
        return val

class __extend__(Number):
    def call(self, context):
        return W_Number(self.num)

class __extend__(Plus):
    def call(self, context=None):
        left = self.left.call(context).GetValue()
        right = self.right.call(context).GetValue()
        prim_left = left.ToPrimitive()
        prim_right = right.ToPrimitive()
        # INSANE
        if isinstance(prim_left, W_String) or isinstance(prim_right, W_String):
            str_left = prim_left.ToString()
            str_right = prim_right.ToString()
            return W_String(str_left + str_right)
        else:
            num_left = prim_left.ToNumber()
            num_right = prim_right.ToNumber()
            # XXX: obey all the rules
            return W_Number(num_left + num_right)
        #return self.left.call(context).add(self.right.call(context))

class __extend__(Semicolon):
    def call(self, context=None):
        self.expr.call(context)

class __extend__(Identifier):
    def call(self, context=None):
        return context.access(self.name)

class __extend__(Script):
    def call(self, context=None):
        new_context = ExecutionContext(context)
        for node in self.nodes:
            node.call(new_context)

class __extend__(Call):
    def call(self, context=None):
        assert self.identifier.name == 'print'
        writer(",".join([str(i) for i in self.arglist.call(context)]))

class __extend__(List):
    def call(self, context=None):
        return [node.call(context) for node in self.nodes]

class __extend__(String):
    def call(self, context=None):
        return W_String(self.strval)
