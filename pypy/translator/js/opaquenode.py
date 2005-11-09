from pypy.translator.js.node import Node
from pypy.rpython.lltypesystem import lltype


class OpaqueNode(Node):
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "null"

    def writeglobalconstants(self, codewriter):
        # XXX Dummy - not sure what what we want
        pass
