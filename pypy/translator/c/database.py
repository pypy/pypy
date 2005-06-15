from pypy.rpython.lltype import Primitive, Ptr, typeOf
from pypy.rpython.lltype import Struct, Array, FuncType, PyObject, Void
from pypy.rpython.lltype import ContainerType, pyobjectptr, OpaqueType, GcStruct
from pypy.rpython.rmodel import getfunctionptr
from pypy.objspace.flow.model import Constant
from pypy.translator.c.primitive import PrimitiveName, PrimitiveType
from pypy.translator.c.primitive import PrimitiveErrorValue
from pypy.translator.c.node import StructDefNode, ArrayDefNode
from pypy.translator.c.node import ContainerNodeClass
from pypy.translator.c.support import cdecl, CNameManager, ErrorValue
from pypy.translator.c.pyobj import PyObjMaker

# ____________________________________________________________

class LowLevelDatabase:

    def __init__(self, translator=None):
        self.translator = translator
        self.structdefnodes = {}
        self.structdeflist = []
        self.containernodes = {}
        self.containerlist = []
        self.namespace = CNameManager()
        self.pyobjmaker = PyObjMaker(self.namespace, self.get, translator)

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
            node.setup()
            self.structdeflist.append(node)
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
                if T.ARGS[i] != Void:
                    argtype = self.gettype(T.ARGS[i])
                    try:
                        argname = argnames[i]
                    except IndexError:
                        argname = ''
                    argtypes.append(cdecl(argtype, argname))
            argtypes = ', '.join(argtypes) or 'void'
            return resulttype.replace('@', '(@)(%s)' % argtypes)
        elif isinstance(T, OpaqueType):
            if T.tag == 'RuntimeTypeInfo':
                return 'void (@)(void *)'   # void dealloc_xx(struct xx *)
            else:
                raise Exception("don't know about opaque type %r" % (T,))
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

    def cincrefstmt(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if T.TO == PyObject:
                return 'Py_XINCREF(%s);' % expr
            else:
                defnode = self.gettypedefnode(T.TO)
                if defnode.refcount is not None:
                    return 'if (%s) %s->%s++;' % (expr, expr, defnode.refcount)
        return ''

    def cdecrefstmt(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if T.TO == PyObject:
                return 'Py_XDECREF(%s);' % expr
            else:
                defnode = self.gettypedefnode(T.TO)
                if defnode.refcount is not None:
                    return 'if (%s && !--%s->%s) %s(%s);' % (expr, expr,
                                                             defnode.refcount,
                                               defnode.deallocator or 'OP_FREE',
                                                             expr)
        return ''

    def complete(self):
        i = 0
        while True:
            self.pyobjmaker.collect_initcode()
            if i == len(self.containerlist):
                break
            node = self.containerlist[i]
            for value in node.enum_dependencies():
                if isinstance(typeOf(value), ContainerType):
                    self.getcontainernode(value)
                else:
                    self.get(value)
            i += 1

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

    def pre_include_code_lines(self):
        # generate some #defines that go before the #include to control
        # what g_exception.h does
        if self.translator is not None and self.translator.rtyper is not None:
            exceptiondata = self.translator.rtyper.getexceptiondata()

            TYPE = exceptiondata.lltype_of_exception_type
            assert isinstance(TYPE, Ptr)
            typename = self.gettype(TYPE)
            yield '#define RPYTHON_EXCEPTION_VTABLE %s' % cdecl(typename, '')

            TYPE = exceptiondata.lltype_of_exception_value
            assert isinstance(TYPE, Ptr)
            typename = self.gettype(TYPE)
            yield '#define RPYTHON_EXCEPTION        %s' % cdecl(typename, '')

            fnptr = getfunctionptr(self.translator,
                                   exceptiondata.ll_exception_match)
            fnname = self.get(fnptr)
            yield '#define RPYTHON_EXCEPTION_MATCH  %s' % (fnname,)

            fnptr = getfunctionptr(self.translator,
                                   exceptiondata.ll_type_of_exc_inst)
            fnname = self.get(fnptr)
            yield '#define RPYTHON_TYPE_OF_EXC_INST %s' % (fnname,)

            fnptr = getfunctionptr(self.translator,
                                   exceptiondata.ll_pyexcclass2exc)
            fnname = self.get(fnptr)
            yield '#define RPYTHON_PYEXCCLASS2EXC   %s' % (fnname,)

            for pyexccls in exceptiondata.standardexceptions:
                exc_llvalue = exceptiondata.ll_pyexcclass2exc(
                    pyobjectptr(pyexccls))
                # strange naming here because the macro name must be
                # a substring of PyExc_%s
                yield '#define Exc_%s\t%s' % (
                    pyexccls.__name__, self.get(exc_llvalue))

            self.complete()   # because of the get() and gettype() above
