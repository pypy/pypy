import sys
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, PyObject, ContainerType, GcArray, GcStruct, \
     RuntimeTypeInfo, getRuntimeTypeInfo
from pypy.rpython.memory import gctransform
from pypy.rpython.lltypesystem import lltype, llmemory

PyObjPtr = Ptr(PyObject)

class BasicGcPolicy:
    
    def __init__(self, db, thread_enabled=False):
        self.db = db
        self.thread_enabled = thread_enabled

    def common_gcheader_definition(self, defnode):
        return []

    def common_gcheader_initdata(self, defnode):
        return []

    def struct_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def struct_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def array_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def array_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def gc_libraries(self):
        return []

    def pre_pre_gc_code(self): # code that goes before include g_prerequisite.h
        return []

    def pre_gc_code(self):
        return []

    def gc_startup_code(self):
        return []

    def OP_GC_PUSH_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        if expr == 'NULL':
            return ''
        return 'Py_XINCREF(%s);' % expr

    def OP_GC_POP_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        return 'Py_XDECREF(%s);' % expr


class RefcountingInfo:
    static_deallocator = None

from pypy.rpython.objectmodel import Symbolic
class REFCOUNT_IMMORTAL(Symbolic):
    def annotation(self):
        from pypy.annotation.model import SomeInteger
        return SomeInteger()
    def lltype(self):
        return lltype.Signed

class RefcountingGcPolicy(BasicGcPolicy):
    transformerclass = gctransform.RefcountingGCTransformer

    def common_gcheader_definition(self, defnode):
        return [('refcount', lltype.Signed)]

    def common_gcheader_initdata(self, defnode):
        return [REFCOUNT_IMMORTAL()]

    # for structs

    def struct_setup(self, structdefnode, rtti):
        if rtti is not None:
            transformer = structdefnode.db.gctransformer
            fptr = transformer.static_deallocation_funcptr_for_type(
                structdefnode.STRUCT)
            structdefnode.gcinfo = RefcountingInfo()
            structdefnode.gcinfo.static_deallocator = structdefnode.db.get(fptr)

    # for arrays

    def array_setup(self, arraydefnode):
        pass

    # for rtti node

    def rtti_type(self):
        return 'void (@)(void *)'   # void dealloc_xx(struct xx *)

    def rtti_node_factory(self):
        return RefcountingRuntimeTypeInfo_OpaqueNode

    # zero malloc impl

    def zero_malloc(self, TYPE, esize, eresult):
        assert TYPE._gcstatus()   # we don't really support this
        return 'OP_ZERO_MALLOC(%s, %s);' % (esize,
                                            eresult)

    def OP_GC_CALL_RTTI_DESTRUCTOR(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        line = '%s(%s);' % (args[0], ', '.join(args[1:]))
        return line	
    
    def OP_GC_FREE(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        return 'OP_FREE(%s);' % (args[0], )    

    def OP_GC_FETCH_EXCEPTION(self, funcgen, op):
        result = funcgen.expr(op.result)
        return ('%s = RPyFetchExceptionValue();\n'
                'RPyClearException();') % (result, )

    def OP_GC_RESTORE_EXCEPTION(self, funcgen, op):
        argh = funcgen.expr(op.args[0])
        return 'if (%s != NULL) RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(%s), %s);' % (argh, argh, argh)

    def OP_GC__COLLECT(self, funcgen, op):
        return ''


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
        self.implementationtypename = 'void (@)(void *)'
        self.name = defnode.gcinfo.static_deallocator
        self.ptrname = '((void (*)(void *)) %s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []



class BoehmInfo:
    finalizer = None

class BoehmGcPolicy(BasicGcPolicy):
    transformerclass = gctransform.BoehmGCTransformer

    def setup_gcinfo(self, defnode):
        transformer = defnode.db.gctransformer
        fptr = transformer.finalizer_funcptr_for_type(defnode.LLTYPE)
        if fptr:
            defnode.gcinfo = BoehmInfo()
            defnode.gcinfo.finalizer = defnode.db.get(fptr)

    def array_setup(self, arraydefnode):
        self.setup_gcinfo(arraydefnode)

    def struct_setup(self, structdefnode, rtti):
        self.setup_gcinfo(structdefnode)

    def rtti_type(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode

    def zero_malloc(self, TYPE, esize, eresult):
        gcinfo = self.db.gettypedefnode(TYPE).gcinfo
        assert TYPE._gcstatus()   # _is_atomic() depends on this!
        is_atomic = TYPE._is_atomic()
        is_varsize = TYPE._is_varsize()
        result = 'OP_BOEHM_ZERO_MALLOC(%s, %s, %d, %d);' % (esize,
                                                            eresult,
                                                            is_atomic,
                                                            is_varsize)
        if gcinfo and gcinfo.finalizer:
            result += ('\nGC_REGISTER_FINALIZER(%s, (GC_finalization_proc)%s, NULL, NULL, NULL);'
                       % (eresult, gcinfo.finalizer))
        return result

    def gc_libraries(self):
        if sys.platform == 'win32':
            return ['gc_pypy']
        return ['gc']

    def pre_pre_gc_code(self):
        if sys.platform == "linux2":
            yield "#define _REENTRANT 1"
            yield "#define GC_LINUX_THREADS 1"
            yield "#define GC_REDIRECT_TO_LOCAL 1"
            yield '#include <gc/gc_local_alloc.h>'
            yield '#define USING_BOEHM_GC'
        else:
            yield '#include <gc/gc.h>'
            yield '#define USING_BOEHM_GC'

    def gc_startup_code(self):
        if sys.platform == 'win32':
            pass # yield 'assert(GC_all_interior_pointers == 0);'
        else:
            yield 'GC_all_interior_pointers = 0;'
        yield 'GC_init();'


    def OP_GC_FETCH_EXCEPTION(self, funcgen, op):
        result = funcgen.expr(op.result)
        return ('%s = RPyFetchExceptionValue();\n'
                'RPyClearException();') % (result, )

    def OP_GC_RESTORE_EXCEPTION(self, funcgen, op):
        argh = funcgen.expr(op.args[0])
        return 'if (%s != NULL) RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(%s), %s);' % (argh, argh, argh)

    def OP_GC__COLLECT(self, funcgen, op):
        return 'GC_gcollect(); GC_invoke_finalizers();'


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

    def pre_pre_gc_code(self):
        yield '#define USING_NO_GC'

# the framework GC policy -- we are very optimistic tonight

class FrameworkGcPolicy(NoneGcPolicy):
    transformerclass = gctransform.FrameworkGCTransformer

    def gc_startup_code(self):
        fnptr = self.db.gctransformer.frameworkgc_setup_ptr.value
        yield '%s();' % (self.db.get(fnptr),)

    def pre_gc_code(self):
        return []

    def OP_GC_RELOAD_POSSIBLY_MOVED(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        return '%s = %s; /* for moving GCs */' % (args[1], args[0])

    def common_gcheader_definition(self, defnode):
        # XXX assumes mark and sweep
        return [('typeid', lltype.Signed)]

    def common_gcheader_initdata(self, defnode):
        # XXX this more or less assumes mark-and-sweep gc
        o = defnode.obj
        while True:
            n = o._parentstructure()
            if n is None:
                break
            o = n
        return [defnode.db.gctransformer.id_of_type[typeOf(o)] << 1]
