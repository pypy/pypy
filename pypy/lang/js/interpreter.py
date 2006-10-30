
from pypy.lang.js.astgen import *

class __extend__(Number):
    def call(self):
        return self.num

class __extend__(Plus):
    def call(self):
        return self.left.call() + self.right.call()

class __extend__(Semicolon):
    def call(self):
        self.expr.call()

class __extend__(Script):
    def call(self):
        for node in self.nodes:
            node.call()

class __extend__(Call):
    def call(self):
        assert self.identifier.name == 'print'
        print ",".join([str(i) for i in self.arglist.call()])

class __extend__(List):
    def call(self):
        return [node.call() for node in self.nodes]
