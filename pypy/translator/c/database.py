from pypy.rpython.lltypesystem.lltype import \
     Primitive, Ptr, typeOf, RuntimeTypeInfo, \
     Struct, Array, FuncType, PyObject, Void, \
     ContainerType, OpaqueType
from pypy.translator.c.primitive import PrimitiveName, PrimitiveType
from pypy.translator.c.primitive import PrimitiveErrorValue
from pypy.translator.c.node import StructDefNode, ArrayDefNode
from pypy.translator.c.node import ContainerNodeFactory, ExtTypeOpaqueDefNode
from pypy.translator.c.support import cdecl, CNameManager, ErrorValue
from pypy.translator.c.pyobj import PyObjMaker
from pypy.translator.c.support import log

# ____________________________________________________________

class LowLevelDatabase:

    def __init__(self, translator=None, standalone=False, gcpolicy=None, thread_enabled=False):
        self.translator = translator
        self.standalone = standalone
        self.structdefnodes = {}
        self.pendingsetupnodes = []
        self.containernodes = {}
        self.containerlist = []
        self.completedcontainers = 0
        self.containerstats = {}
        self.externalfuncs = {}
        self.infs = []
        self.namespace = CNameManager()
        if not standalone:
            self.pyobjmaker = PyObjMaker(self.namespace, self.get, translator)
        if gcpolicy is None:
            from pypy.translator.c import gc
            gcpolicy = gc.RefcountingGcPolicy
        self.gcpolicy = gcpolicy(self, thread_enabled)
        self.completed = False

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
            elif isinstance(T, OpaqueType) and hasattr(T, '_exttypeinfo'):
                node = ExtTypeOpaqueDefNode(self, T)
            else:
                raise Exception("don't know about %r" % (T,))
            self.structdefnodes[key] = node
            self.pendingsetupnodes.append(node)
        return node

    def gettype(self, T, varlength=1, who_asks=None, argnames=[]):
        if isinstance(T, Primitive):
            return PrimitiveType[T]
        elif isinstance(T, Ptr):
            typename = self.gettype(T.TO)   # who_asks not propagated
            return typename.replace('@', '*@')
        elif isinstance(T, (Struct, Array)):
            node = self.gettypedefnode(T, varlength=varlength)
            if who_asks is not None:
                who_asks.dependencies[node] = True
            return 'struct %s @' % node.name
        elif T == PyObject:
            return 'PyObject @'
        elif isinstance(T, FuncType):
            resulttype = self.gettype(T.RESULT)
            argtypes = []
            for i in range(len(T.ARGS)):
                if T.ARGS[i] is not Void:
                    argtype = self.gettype(T.ARGS[i])
                    try:
                        argname = argnames[i]
                    except IndexError:
                        argname = ''
                    argtypes.append(cdecl(argtype, argname))
            argtypes = ', '.join(argtypes) or 'void'
            return resulttype.replace('@', '(@)(%s)' % argtypes)
        elif isinstance(T, OpaqueType):
            if T == RuntimeTypeInfo:
                return  self.gcpolicy.rtti_type()
            elif hasattr(T, '_exttypeinfo'):
                # for external types (pypy.rpython.extfunctable.declaretype())
                node = self.gettypedefnode(T, varlength=varlength)
                if who_asks is not None:
                    who_asks.dependencies[node] = True
                return 'struct %s @' % node.name
            else:
                raise Exception("don't know about opaque type %r" % (T,))
        else:
            raise Exception("don't know about type %r" % (T,))

    def getcontainernode(self, container):
        try:
            node = self.containernodes[container]
        except KeyError:
            T = typeOf(container)
            nodefactory = ContainerNodeFactory[T.__class__]
            node = nodefactory(self, T, container)
            self.containernodes[container] = node
            self.containerlist.append(node)
            kind = getattr(node, 'nodekind', '?')
            self.containerstats[kind] = self.containerstats.get(kind, 0) + 1
        return node

    def get(self, obj):
        if isinstance(obj, ErrorValue):
            T = obj.TYPE
            if isinstance(T, Primitive):
                return PrimitiveErrorValue[T]
            elif isinstance(T, Ptr):
                return 'NULL'
            else:
                raise Exception("don't know about %r" % (T,))
        else:
            T = typeOf(obj)
            if isinstance(T, Primitive):
                return PrimitiveName[T](obj)
            elif isinstance(T, Ptr):
                if obj:   # test if the ptr is non-NULL
                    node = self.getcontainernode(obj._obj)
                    return node.ptrname
                else:
                    return 'NULL'
            else:
                raise Exception("don't know about %r" % (obj,))

    def complete(self, show_progress=True):
        def dump():
            lst = ['%s: %d' % keyvalue
                   for keyvalue in self.containerstats.items()]
            lst.sort()
            log.event('%8d nodes  [ %s ]' % (i, '  '.join(lst)))
        i = self.completedcontainers
        if show_progress:
            show_i = (i//1000 + 1) * 1000
        else:
            show_i = -1
        while True:
            if hasattr(self, 'pyobjmaker'):
                self.pyobjmaker.collect_initcode()
            while self.pendingsetupnodes:
                lst = self.pendingsetupnodes
                self.pendingsetupnodes = []
                for nodedef in lst:
                    nodedef.setup()
            if i == len(self.containerlist):
                break
            node = self.containerlist[i]
            for value in node.enum_dependencies():
                if isinstance(typeOf(value), ContainerType):
                    self.getcontainernode(value)
                else:
                    self.get(value)
            i += 1
            self.completedcontainers = i
            if i == show_i:
                dump()
                show_i += 1000
        self.completed = True
        if show_progress:
            dump()

    def globalcontainers(self):
        for node in self.containerlist:
            if node.globalcontainer:
                yield node

    def get_lltype_of_exception_value(self):
        if self.translator is not None and self.translator.rtyper is not None:
            exceptiondata = self.translator.rtyper.getexceptiondata()
            return exceptiondata.lltype_of_exception_value
        else:
            return Ptr(PyObject)

    def getstructdeflist(self):
        # return the StructDefNodes sorted according to dependencies
        result = []
        seen = {}
        def produce(node):
            if node not in seen:
                for othernode in node.dependencies:
                    produce(othernode)
                result.append(node)
                seen[node] = True
        for node in self.structdefnodes.values():
            produce(node)
        return result
