
from pypy.lang.js.astgen import *
from pypy.lang.js.context import ExecutionContext

def writer(x):
    print x

class __extend__(Assign):
    def call(self, context):
        val = self.expr.call(context)
        context.assign(self.identifier.name, val)
        return val

class __extend__(Number):
    def call(self, context):
        return self.num

class __extend__(Plus):
    def call(self, context=None):
        return self.left.call(context) + self.right.call(context)

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
