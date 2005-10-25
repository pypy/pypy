import sys
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, PyObject, ContainerType, Array, GcArray, Struct, GcStruct, \
     RuntimeTypeInfo, getRuntimeTypeInfo

PyObjPtr = Ptr(PyObject)

class BasicGcPolicy:
    
    def __init__(self, db):
        self.db = db

    def pyobj_incref(self, expr, T):
        return 'Py_XINCREF(%s);' % expr

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

    def push_alive_nopyobj(self, expr, T):
        return ''

    def pop_alive_nopyobj(self, expr, T):
        return ''

    def push_alive_op_result(self, opname, expr, T):
        return ''

    def gcheader_field_name(self, defnode):
        return None

    def common_gcheader_definition(self, defnode):
        return ''

    def common_after_definition(self, defnode):
        return []

    def common_gcheader_initializationexpr(self, defnode):
        return ''

    struct_gcheader_definition = common_gcheader_definition
    struct_after_definition = common_after_definition
    struct_gcheader_initializationexpr = common_gcheader_initializationexpr

    def prepare_nested_gcstruct(self, structdefnode, INNER):
        pass

    array_gcheader_definition = common_gcheader_definition
    array_after_definition = common_after_definition
    array_gcheader_initializationexpr = common_gcheader_initializationexpr

    def gc_libraries(self):
        return []

    def pre_pre_gc_code(self): # code that goes before include g_prerequisite.h
        return []

    def pre_gc_code(self):
        return []

    def gc_startup_code(self):
        return []

class RefcountingInfo:
    deallocator = None
    static_deallocator = None

class RefcountingGcPolicy(BasicGcPolicy):

    def push_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            return 'pypy_IncRf_%s(%s);' % (defnode.barename, expr)

    def pop_alive_nopyobj(self, expr, T):
        defnode = self.db.gettypedefnode(T.TO)
        if defnode.gcheader is not None:
            return 'pypy_DecRf_%s(%s);' % (defnode.barename, expr)

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
            result.insert(0, '%s = %s;' % (
                cdecl(self.db.gettype(T), 'prev'),
                targetexpr))
            result.append(decrefstmt)
            result[:] = ['\t%s' % line for line in result]
            result[0] = '{' + result[0]
            result.append('}')

    def generic_dealloc(self, expr, T):
        db = self.db
        if isinstance(T, Ptr) and T._needsgc():
            line = self.pop_alive(expr, T)
            if line:
                yield line
        elif isinstance(T, ContainerType):
            defnode = db.gettypedefnode(T)
            from pypy.translator.c.node import ExtTypeOpaqueDefNode
            if isinstance(defnode, ExtTypeOpaqueDefNode):
                yield 'RPyOpaqueDealloc_%s(&(%s));' % (defnode.T.tag, expr)
            else:
                for line in defnode.visitor_lines(expr, self.generic_dealloc):
                    yield line

    def gcheader_field_name(self, defnode):
        return 'refcount'

    def common_gcheader_definition(self, defnode):
        return 'long refcount;'

    def common_after_definition(self, defnode):
        if defnode.gcinfo:
            gcinfo = defnode.gcinfo
            if gcinfo.deallocator:
                yield 'void %s(struct %s *);' % (gcinfo.deallocator, defnode.name)
        if defnode.gcheader is not None:
            dealloc = 'OP_FREE'
            if defnode.gcinfo:
                dealloc = defnode.gcinfo.deallocator or dealloc
            yield '#define pypy_IncRf_%s(x) if (x) (x)->%s++' % (
                defnode.barename, defnode.gcheader,)
            yield '#define pypy_DecRf_%s(x) if ((x) && !--(x)->%s) %s(x)' % (
                defnode.barename, defnode.gcheader, dealloc)

    def common_gcheader_initializationexpr(self, defnode):
        return 'REFCOUNT_IMMORTAL,'

    def deallocator_lines(self, defnode, prefix):
        return defnode.visitor_lines(prefix, self.generic_dealloc)

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
                if list(self.deallocator_lines(structdefnode, '')):
                    gcinfo.static_deallocator = gcinfo.deallocator
                else:
                    gcinfo.deallocator = None

    struct_gcheader_definition = common_gcheader_definition

    struct_after_definition = common_after_definition

    def struct_implementationcode(self, structdefnode):
        if structdefnode.gcinfo:
            gcinfo = structdefnode.gcinfo
            if gcinfo.static_deallocator:
                yield 'void %s(struct %s *p) {' % (gcinfo.static_deallocator,
                                               structdefnode.name)
                for line in self.deallocator_lines(structdefnode, '(*p)'):
                    yield '\t' + line
                yield '\tOP_FREE(p);'
                yield '}'
            if gcinfo.deallocator and gcinfo.deallocator != gcinfo.static_deallocator:
                yield 'void %s(struct %s *p) {' % (gcinfo.deallocator, structdefnode.name)
                yield '\tvoid (*staticdealloc) (void *);'
                # the refcount should be 0; temporarily bump it to 1
                yield '\tp->%s = 1;' % (structdefnode.gcheader,)
                # cast 'p' to the type expected by the rtti_query function
                yield '\tstaticdealloc = %s((%s) p);' % (
                    gcinfo.rtti_query_funcptr,
                    cdecl(gcinfo.rtti_query_funcptr_argtype, ''))
                yield '\tif (!--p->%s)' % (structdefnode.gcheader,)
                yield '\t\tstaticdealloc(p);'
                yield '}'


    struct_gcheader_initializationexpr = common_gcheader_initializationexpr

    # for arrays

    def array_setup(self, arraydefnode):
        if arraydefnode.gcheader and list(self.deallocator_lines(arraydefnode, '')):
            gcinfo = arraydefnode.gcinfo = RefcountingInfo()
            gcinfo.deallocator = self.db.namespace.uniquename('dealloc_'+arraydefnode.barename)

    array_gcheader_definition = common_gcheader_definition

    array_after_definition = common_after_definition

    def array_implementationcode(self, arraydefnode):
        if arraydefnode.gcinfo:
            gcinfo = arraydefnode.gcinfo
            if gcinfo.deallocator:
                yield 'void %s(struct %s *a) {' % (gcinfo.deallocator, arraydefnode.name)
                for line in self.deallocator_lines(arraydefnode, '(*a)'):
                    yield '\t' + line
                yield '\tOP_FREE(a);'
                yield '}'

    array_gcheader_initializationexpr = common_gcheader_initializationexpr

    # for rtti node

    def rtti_type(self):
        return 'void (@)(void *)'   # void dealloc_xx(struct xx *)

    def rtti_node_factory(self):
        return RefcountingRuntimeTypeInfo_OpaqueNode

    # zero malloc impl

    def zero_malloc(self, TYPE, esize, eresult, err):
        assert TYPE._gcstatus()   # we don't really support this
        return 'OP_ZERO_MALLOC(%s, %s, %s);' % (esize,
                                                eresult,
                                                err)

class RefcountingRuntimeTypeInfo_OpaqueNode(ContainerNode):
    nodekind = 'refcnt rtti'
    globalcontainer = True
    includes = ()
    typename = 'void (@)(void *)'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, GcStruct)
        self.db = db
        self.T = T
        self.obj = obj
        defnode = db.gettypedefnode(obj.about)
        self.implementationtypename = 'void (@)(struct %s *)' % (
            defnode.name,)
        self.name = defnode.gcinfo.static_deallocator
        self.ptrname = '((void (*)(void *)) %s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []



class BoehmGcInfo:
    finalizer = None

class BoehmGcPolicy(BasicGcPolicy):

    write_barrier = RefcountingGcPolicy.write_barrier.im_func

    generic_dealloc = RefcountingGcPolicy.generic_dealloc.im_func

    deallocator_lines = RefcountingGcPolicy.deallocator_lines.im_func

    # for arrays

    def array_setup(self, arraydefnode):
        if isinstance(arraydefnode.LLTYPE, GcArray) and list(self.deallocator_lines(arraydefnode, '')):
            gcinfo = arraydefnode.gcinfo = RefcountingInfo()
            gcinfo.finalizer = self.db.namespace.uniquename('finalize_'+arraydefnode.barename)

    def array_implementationcode(self, arraydefnode):
        if arraydefnode.gcinfo:
            gcinfo = arraydefnode.gcinfo
            if gcinfo.finalizer:
                yield 'void %s(GC_PTR obj, GC_PTR ignore) {' % (gcinfo.finalizer)
                yield '\tstruct %s *a = (struct %s *)obj;' % (arraydefnode.name, arraydefnode.name)
                for line in self.deallocator_lines(arraydefnode, '(*a)'):
                    yield '\t' + line
                yield '}'

    # for structs
    def struct_setup(self, structdefnode, rtti):
        if isinstance(structdefnode.LLTYPE, GcStruct) and list(self.deallocator_lines(structdefnode, '')):
            gcinfo = structdefnode.gcinfo = RefcountingInfo()
            gcinfo.finalizer = self.db.namespace.uniquename('finalize_'+structdefnode.barename)

    def struct_implementationcode(self, structdefnode):
        if structdefnode.gcinfo:
            gcinfo = structdefnode.gcinfo
            if gcinfo.finalizer:
                yield 'void %s(GC_PTR obj, GC_PTR ignore) {' % gcinfo.finalizer
                yield '\tstruct %s *p = (struct %s *)obj;' % (structdefnode.name, structdefnode.name)
                for line in self.deallocator_lines(structdefnode, '(*p)'):
                    yield '\t' + line
                yield '}'

    # for rtti node

    def rtti_type(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode

    # zero malloc impl

    def zero_malloc(self, TYPE, esize, eresult, err):
        gcinfo = self.db.gettypedefnode(TYPE).gcinfo
        assert TYPE._gcstatus()   # _is_atomic() depends on this!
        is_atomic = TYPE._is_atomic()
        is_varsize = TYPE._is_varsize()
        result = 'OP_BOEHM_ZERO_MALLOC(%s, %s, %d, %d, %s);' % (esize,
                                                                eresult,
                                                                is_atomic,
                                                                is_varsize,
                                                                err)
        if gcinfo and gcinfo.finalizer:
            result += ('\nGC_REGISTER_FINALIZER(%s, %s, NULL, NULL, NULL);'
                       % (eresult, gcinfo.finalizer))
        return result

    def gc_libraries(self):
        if sys.platform == 'win32':
            return ['gc_pypy']
        return ['gc']

    def pre_pre_gc_code(self):
        #if sys.platform == "linux2":
        #    yield "#define _REENTRANT 1"
        #    yield "#define GC_LINUX_THREADS 1"
        yield '#include <gc/gc.h>'
        yield '#define USING_BOEHM_GC'

    def gc_startup_code(self):
        if sys.platform == 'win32':
            yield 'assert(GC_all_interior_pointers == 0);'
        else:
            yield 'GC_all_interior_pointers = 0;'
        yield 'GC_INIT();'


class BoehmGcRuntimeTypeInfo_OpaqueNode(ContainerNode):
    nodekind = 'boehm rtti'
    globalcontainer = True
    includes = ()
    typename = 'char @'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, GcStruct)
        self.db = db
        self.T = T
        self.obj = obj
        defnode = db.gettypedefnode(obj.about)
        self.implementationtypename = self.typename
        self.name = self.db.namespace.uniquename('g_rtti_v_'+ defnode.barename)
        self.ptrname = '(&%s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        yield 'char %s  /* uninitialized */;' % self.name

# to get an idea how it looks like with no refcount/gc at all

class NoneGcPolicy(BoehmGcPolicy):

    zero_malloc = RefcountingGcPolicy.zero_malloc.im_func
    gc_libraries = RefcountingGcPolicy.gc_libraries.im_func
    gc_startup_code = RefcountingGcPolicy.gc_startup_code.im_func
    rtti_type = RefcountingGcPolicy.rtti_type.im_func

    def pre_pre_gc_code(self):
        yield '#define USING_NO_GC'

    def struct_implementationcode(self, structdefnode):
        return []
    array_implementationcode = struct_implementationcode
