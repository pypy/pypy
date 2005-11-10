from pypy.translator.js.node import Node


class OpaqueNode(Node):
    def __init__(self, db, value):
        self.db    = db
        self.value = value
        self.ref   = "null"
