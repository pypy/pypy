
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
