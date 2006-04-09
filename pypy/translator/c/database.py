from pypy.rpython.lltypesystem.lltype import \
     Primitive, Ptr, typeOf, RuntimeTypeInfo, \
     Struct, Array, FuncType, PyObject, Void, \
     ContainerType, OpaqueType, FixedSizeArray
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.llmemory import Address
from pypy.rpython.memory.lladdress import NULL
from pypy.translator.c.primitive import PrimitiveName, PrimitiveType
from pypy.translator.c.primitive import PrimitiveErrorValue
from pypy.translator.c.node import StructDefNode, ArrayDefNode
from pypy.translator.c.node import FixedSizeArrayDefNode
from pypy.translator.c.node import ContainerNodeFactory, ExtTypeOpaqueDefNode
from pypy.translator.c.support import cdecl, CNameManager, ErrorValue
from pypy.translator.c.pyobj import PyObjMaker
from pypy.translator.c.support import log
from pypy.translator.c.extfunc import do_the_getting
from pypy.translator.c.exceptiontransform import ExceptionTransformer
from pypy import conftest

# ____________________________________________________________

class LowLevelDatabase(object):

    def __init__(self, translator=None, standalone=False, gcpolicy=None, thread_enabled=False,
                 instantiators={}):
        self.translator = translator
        self.standalone = standalone
        self.structdefnodes = {}
        self.pendingsetupnodes = []
        self.containernodes = {}
        self.containerlist = []
        self.latercontainerlist = []
        self.completedcontainers = 0
        self.containerstats = {}
        self.externalfuncs = {}
        self.helper2ptr = {}
        
        self.infs = []
        self.namespace = CNameManager()
        if not standalone:
            self.pyobjmaker = PyObjMaker(self.namespace, self.get, translator, instantiators)
        if gcpolicy is None:
            from pypy.translator.c import gc
            polname = conftest.option.gcpolicy
            if polname is not None:
                if polname == 'boehm':
                    gcpolicy = gc.BoehmGcPolicy
                elif polname == 'ref':
                    gcpolicy = gc.RefcountingGcPolicy
                elif polname == 'none':
                    gcpolicy = gc.NoneGcPolicy
                elif polname == 'framework':
                    gcpolicy = gc.FrameworkGcPolicy
                else:
                    assert False, "unknown gc policy %r"%polname
            else:
                gcpolicy = gc.RefcountingGcPolicy
        if translator is None or translator.rtyper is None:
            self.exctransformer = None
        else:
            self.exctransformer = ExceptionTransformer(translator)
        self.gcpolicy = gcpolicy(self, thread_enabled)
        self.gctransformer = gcpolicy.transformerclass(translator)
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
                if isinstance(T, FixedSizeArray):
                    node = FixedSizeArrayDefNode(self, T)
                else:
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
            if isinstance(T.TO, FixedSizeArray):
                # /me blames C
                node = self.gettypedefnode(T.TO)
                return node.getptrtype()
            else:
                typename = self.gettype(T.TO)   # who_asks not propagated
                return typename.replace('@', '*@')
        elif isinstance(T, (Struct, Array)):
            node = self.gettypedefnode(T, varlength=varlength)
            if who_asks is not None:
                who_asks.dependencies[node] = True
            return node.gettype()
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
            assert not self.completed
            T = typeOf(container)
            if isinstance(T, (lltype.Array, lltype.Struct)):
                if hasattr(self.gctransformer, 'consider_constant'):
                    self.gctransformer.consider_constant(T, container)
            nodefactory = ContainerNodeFactory[T.__class__]
            node = nodefactory(self, T, container)
            self.containernodes[container] = node
            if getattr(container, 'isgchelper', False):
                self.latercontainerlist.append(node)
            else:
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
                return PrimitiveName[T](obj, self)
            elif isinstance(T, Ptr):
                if obj:   # test if the ptr is non-NULL
                    node = self.getcontainernode(obj._obj)
                    return node.ptrname
                else:
                    return 'NULL'
            else:
                raise Exception("don't know about %r" % (obj,))

    def complete(self, show_progress=True):
        assert not self.completed
        if self.translator and self.translator.rtyper:
            do_the_getting(self, self.translator.rtyper)
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
        work_to_do = True
        is_later_yet = False
        while work_to_do:
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
            work_to_do = False
            if not is_later_yet:
                newgcdependencies = self.gctransformer.finish()
                if newgcdependencies:
                    work_to_do = True
                    for value in newgcdependencies:
                        if isinstance(typeOf(value), ContainerType):
                            self.getcontainernode(value)
                        else:
                            self.get(value)
                is_later_yet = True
            if self.latercontainerlist:
                work_to_do = True
                for node in self.latercontainerlist:
                    node.make_funcgens()
                    self.containerlist.append(node)
                self.latercontainerlist = []
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
