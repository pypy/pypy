from pypy.translator.c.support import cdecl
from pypy.rpython.lltype import typeOf, Ptr, PyObject
from pypy.rpython.lltype import getRuntimeTypeInfo

PyObjPtr = Ptr(PyObject)

class BasicGcPolicy:
    
    def __init__(self, db):
        self.db = db

    def pyobj_incref(self, expr, T):
        if T == PyObjPtr:
            return 'Py_XINCREF(%s);' % expr
        return ''

    def pyobj_decref(self, expr, T):
        return 'Py_XDECREF(%s);' % expr

    def push_alive(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if expr == 'NULL':    # hum
                return ''
            if T.TO == PyObject:
                return self.pyobj_incref(expr, T)
            else:
                return self.push_alive_nopyobj(expr, T)
        return ''

    def pop_alive(self, expr, T):
        if isinstance(T, Ptr) and T._needsgc():
            if T.TO == PyObject:
                return self.pyobj_decref(expr, T)
            else:
                return self.pop_alive_nopyobj(expr, T)
        return ''

class RefcountingInfo:
    deallocator = None
    static_deallocator = None

class RefcountingGcPolicy(BasicGcPolicy):

    def push_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            return 'if (%s) %s->%s++;' % (expr, expr, defnode.gcheader)

    def pop_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            dealloc = 'OP_FREE'
            if defnode.gcinfo:
                dealloc = defnode.gcinfo.deallocator or dealloc
            return 'if (%s && !--%s->%s) %s(%s);' % (expr, expr,
                                                     defnode.gcheader,
                                                     dealloc,
                                                     expr)

    def push_alive_op_result(self, opname, expr, T):
        if opname !='direct_call' and T != PyObjPtr:
            return self.push_alive(expr, T)
        return ''

    def write_barrier(self, result, newvalue, T, targetexpr):  
        decrefstmt = self.pop_alive('prev', T)
        increfstmt = self.push_alive(newvalue, T)
        if increfstmt:
            result.append(increfstmt)
        if decrefstmt:
            result.insert(0, '{ %s = %s;' % (
                cdecl(self.db.gettype(T), 'prev'),
                targetexpr))
            result.append(decrefstmt)
            result.append('}')


    def rtti_type(self):
        return 'void (@)(void *)'   # void dealloc_xx(struct xx *)

    def gcheader_field_name(self, defnode):
        return 'refcount'

    def common_gcheader_definition(self, defnode):
        yield 'long refcount;'

    def common_after_definition(self, defnode):
        if defnode.gcinfo:
            gcinfo = defnode.gcinfo
            if gcinfo.deallocator:
                yield 'void %s(struct %s *);' % (gcinfo.deallocator, defnode.name)

    def common_gcheader_initializationexpr(self, defnode):
        yield 'REFCOUNT_IMMORTAL,'

    # for structs

    def prepare_nested_gcstruct(self, structdefnode, INNER):
        # check here that there is enough run-time type information to
        # handle this case
        getRuntimeTypeInfo(structdefnode.STRUCT)
        getRuntimeTypeInfo(INNER)

    def struct_setup(self, structdefnode, rtti):        
        if structdefnode.gcheader:
            db = self.db
            gcinfo = structdefnode.gcinfo = RefcountingInfo()

            gcinfo.deallocator = db.namespace.uniquename('dealloc_'+structdefnode.barename)

            # are two deallocators needed (a dynamic one for DECREF, which checks
            # the real type of the structure and calls the static deallocator) ?
            if rtti is not None:
                gcinfo.static_deallocator = db.namespace.uniquename(
                    'staticdealloc_'+structdefnode.barename)
                fnptr = rtti._obj.query_funcptr
                if fnptr is None:
                    raise NotImplementedError(
                        "attachRuntimeTypeInfo(): please provide a function")
                gcinfo.rtti_query_funcptr = db.get(fnptr)
                T = typeOf(fnptr).TO.ARGS[0]
                gcinfo.rtti_query_funcptr_argtype = db.gettype(T)
            else:
                # is a deallocator really needed, or would it be empty?
                if list(structdefnode.deallocator_lines('')):
                    gcinfo.static_deallocator = gcinfo.deallocator
                else:
                    gcinfo.deallocator = None

    struct_gcheader_definition = common_gcheader_definition

    struct_after_definition = common_after_definition

    def struct_implentationcode(self, structdefnode):
        pass

    struct_gcheader_initialitionexpr = common_gcheader_initializationexpr

    # for arrays

    def array_setup(self, arraydefnode):
        if arraydefnode.gcheader and list(arraydefnode.deallocator_lines('')):
            gcinfo = arraydefnode.gcinfo = RefcountingInfo()
            gcinfo.deallocator = self.db.namespace.uniquename('dealloc_'+arraydefnode.barename)

    array_gcheader_definition = common_gcheader_definition

    array_after_definition = common_after_definition

    def array_implementationcode(self, arraydefnode):
        pass

    array_gcheader_initialitionexpr = common_gcheader_initializationexpr

