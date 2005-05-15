from pypy.translator.gensupp import NameManager
from pypy.rpython.lltypes import Primitive, _PtrType, typeOf
from pypy.rpython.lltypes import Struct, Array, FuncType, PyObject
from pypy.rpython.typer import PyObjPtr
from pypy.objspace.flow.model import Constant
from pypy.translator.c.primitive import PrimitiveName, PrimitiveType
from pypy.translator.c.node import StructDefNode, ArrayDefNode
from pypy.translator.c.node import ContainerNodeClass

# ____________________________________________________________

class LowLevelDatabase:

    def __init__(self):
        self.structdefnodes = {}
        self.structdeflist = []
        self.containernodes = {}
        self.containerlist = []
        self.namespace = NameManager()
        # keywords cannot be reused.  This is the C99 draft's list.
        self.namespace.make_reserved_names('''
           auto      enum      restrict  unsigned
           break     extern    return    void
           case      float     short     volatile
           char      for       signed    while
           const     goto      sizeof    _Bool
           continue  if        static    _Complex
           default   inline    struct    _Imaginary
           do        int       switch
           double    long      typedef
           else      register  union
           ''')

    def gettype(self, T, who_asks=None):
        if isinstance(T, Primitive):
            return PrimitiveType[T]
        elif isinstance(T, _PtrType):
            typename = self.gettype(T.TO)   # who_asks not propagated
            return typename.replace('@', '*@')
        elif isinstance(T, (Struct, Array)):
            try:
                node = self.structdefnodes[T]
            except KeyError:
                if isinstance(T, Struct):
                    node = StructDefNode(self, T)
                else:
                    node = ArrayDefNode(self, T)
                self.structdefnodes[T] = node
                self.structdeflist.append(node)
            if who_asks is not None:
                who_asks.dependencies[node] = True
            return 'struct %s @' % node.name
        elif isinstance(T, PyObject):
            return 'PyObject'
        elif isinstance(T, FuncType):
            resulttype = self.gettype(T.RESULT)
            argtypes = ', '.join([self.gettype(ARG) for ARG in T.ARGS
                                                    if ARG != Void])
            if argtypes:
                argtypes = argtypes.replace('@', '')
            else:
                argtypes = 'void'
            return resulttype.replace('@', '(@)(%s)' % argtypes)
        else:
            raise Exception("don't know about type %r" % (T,))

    def get(self, obj):
        T = typeOf(obj)
        if isinstance(T, Primitive):
            return PrimitiveName[T](obj)
        elif isinstance(T, _PtrType):
            try:
                node = self.containernodes[obj]
            except KeyError:
                nodecls = ContainerNodeClass[T.TO.__class__]
                node = nodecls(self, T.TO, obj)
                self.containernodes[obj] = node
                self.containerlist.append(node)
            return node.ptrname
        else:
            raise Exception("don't know about %r" % (obj,))

    def complete(self):
        for node in self.containerlist:
            for value in node.enum_dependencies(self):
                self.get(value)
