from pypy.rpython.lltypes import Primitive, _PtrType, typeOf
from pypy.rpython.lltypes import Struct, Array, FuncType, PyObject, Void
from pypy.rpython.lltypes import ContainerType
from pypy.rpython.typer import PyObjPtr
from pypy.objspace.flow.model import Constant
from pypy.translator.c.primitive import PrimitiveName, PrimitiveType
from pypy.translator.c.primitive import PrimitiveErrorValue
from pypy.translator.c.node import StructDefNode, ArrayDefNode
from pypy.translator.c.node import ContainerNodeClass
from pypy.translator.c.support import cdecl, CNameManager, ErrorValue

# ____________________________________________________________

class LowLevelDatabase:

    def __init__(self):
        self.structdefnodes = {}
        self.structdeflist = []
        self.containernodes = {}
        self.containerlist = []
        self.namespace = CNameManager()

    def gettypedefnode(self, T, varlength=1):
        if varlength <= 1:
            varlength = 1   # it's C after all
            key = T
        else:
            key = T, varlength
        try:
            node = self.structdefnodes[key]
        except KeyError:
            if isinstance(T, Struct):
                node = StructDefNode(self, T, varlength)
            elif isinstance(T, Array):
                node = ArrayDefNode(self, T, varlength)
            else:
                raise Exception("don't know about %r" % (T,))
            self.structdefnodes[key] = node
            self.structdeflist.append(node)
        return node

    def gettype(self, T, varlength=1, who_asks=None, argnames=[]):
        if isinstance(T, Primitive):
            return PrimitiveType[T]
        elif isinstance(T, _PtrType):
            typename = self.gettype(T.TO)   # who_asks not propagated
            return typename.replace('@', '*@')
        elif isinstance(T, (Struct, Array)):
            node = self.gettypedefnode(T, varlength=varlength)
            if who_asks is not None:
                who_asks.dependencies[node] = True
            return 'struct %s @' % node.name
        elif T == PyObject:
            return 'PyObject'
        elif isinstance(T, FuncType):
            resulttype = self.gettype(T.RESULT)
            argtypes = []
            for i in range(len(T.ARGS)):
                if T.ARGS[i] != Void:
                    argtype = self.gettype(T.ARGS[i])
                    try:
                        argname = argnames[i]
                    except IndexError:
                        argname = ''
                    argtypes.append(cdecl(argtype, argname))
            argtypes = ', '.join(argtypes) or 'void'
            return resulttype.replace('@', '(@)(%s)' % argtypes)
        else:
            raise Exception("don't know about type %r" % (T,))

    def getcontainernode(self, container):
        try:
            node = self.containernodes[container]
        except KeyError:
            T = typeOf(container)
            nodecls = ContainerNodeClass[T.__class__]
            node = nodecls(self, T, container)
            self.containernodes[container] = node
            self.containerlist.append(node)
        return node

    def get(self, obj):
        if isinstance(obj, ErrorValue):
            T = obj.TYPE
            if isinstance(T, Primitive):
                return PrimitiveErrorValue[T]
            else:
                return 'NULL'
        else:
            T = typeOf(obj)
            if isinstance(T, Primitive):
                return PrimitiveName[T](obj)
            elif isinstance(T, _PtrType):
                if obj:   # test if the ptr is non-NULL
                    node = self.getcontainernode(obj._obj)
                    return node.ptrname
                else:
                    return 'NULL'
            else:
                raise Exception("don't know about %r" % (obj,))

    def complete(self):
        for node in self.containerlist:
            for value in node.enum_dependencies():
                if isinstance(typeOf(value), ContainerType):
                    self.getcontainernode(value)
                else:
                    self.get(value)

    def globalcontainers(self):
        for node in self.containerlist:
            if node.globalcontainer:
                yield node

    def write_all_declarations(self, f):
        print >> f
        print >> f, '/********************************************************/'
        print >> f, '/***  Structure definitions                           ***/'
        print >> f
        for node in self.structdeflist:
            for line in node.definition():
                print >> f, line
        print >> f
        print >> f, '/********************************************************/'
        print >> f, '/***  Forward declarations                            ***/'
        print >> f
        for node in self.globalcontainers():
            for line in node.forward_declaration():
                print >> f, line

    def write_all_implementations(self, f):
        print >> f
        print >> f, '/********************************************************/'
        print >> f, '/***  Implementations                                 ***/'
        for node in self.globalcontainers():
            print >> f
            for line in node.implementation():
                print >> f, line
