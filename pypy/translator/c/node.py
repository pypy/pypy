from __future__ import generators
from pypy.translator.gensupp import C_IDENTIFIER
from pypy.rpython.lltypes import Struct, Array, FuncType, PyObject


class StructDefNode:

    def __init__(self, db, STRUCT):
        self.STRUCT = STRUCT
        self.name = db.namespace.uniquename(STRUCT._name)
        self.dependencies = {}
        self.typenames = []
        for name in STRUCT._names:
            T = STRUCT._flds[name]
            self.typenames.append(db.gettype(T, who_asks=self))


class ArrayDefNode:

    def __init__(self, db, ARRAY):
        self.ARRAY = ARRAY
        self.name = db.namespace.uniquename('array')
        self.dependencies = {}
        self.structname = db.gettype(ARRAY.OF, who_asks=self)


class ContainerNode:

    def __init__(self, db, T, obj):
        self.T = T
        self.obj = obj
        self.name = db.namespace.uniquename('g_' + self.basename())
        self.ptrname = '&' + self.name
        self.dependencies = {}
        self.typename = db.gettype(T, who_asks=self)


class StructNode(ContainerNode):
    def basename(self):
        return self.T._name
    def enum_dependencies(self, db):
        for name in self.T._names:
            yield getattr(self.obj, name)

class ArrayNode(ContainerNode):
    def basename(self):
        return 'array'
    def enum_dependencies(self, db):
        for i in range(len(self.obj)):
            yield self.obj[i]

class FuncNode(ContainerNode):
    def basename(self):
        return self.obj._name
    def enum_dependencies(self, db):
        Booom

class PyObjectNode(ContainerNode):
    basename = 'BOOOM'


ContainerNodeClass = {
    Struct:   StructNode,
    Array:    ArrayNode,
    FuncType: FuncNode,
    PyObject: PyObjectNode,
    }
