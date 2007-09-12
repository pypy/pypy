import sys
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, ContainerType, RttiStruct, \
     RuntimeTypeInfo, getRuntimeTypeInfo, top_container
from pypy.rpython.memory.gctransform import \
     refcounting, boehm, framework, stacklessframework
from pypy.rpython.lltypesystem import lltype, llmemory

class BasicGcPolicy(object):
    requires_stackless = False
    
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

    def struct_after_definition(self, defnode):
        return []

    def gc_libraries(self):
        return []

    def pre_pre_gc_code(self): # code that goes before include g_prerequisite.h
        return []

    def pre_gc_code(self):
        return ['typedef void *GC_hidden_pointer;']

    def gc_startup_code(self):
        return []

    def struct_setup(self, structdefnode, rtti):
        return None

    def array_setup(self, arraydefnode):
        return None

    def rtti_type(self):
        return ''

    def OP_GC_PUSH_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        if expr == 'NULL':
            return ''
        return 'Py_XINCREF(%s);' % expr

    def OP_GC_POP_ALIVE_PYOBJ(self, funcgen, op):
        expr = funcgen.expr(op.args[0])
        return 'Py_XDECREF(%s);' % expr

    def OP_GC_SET_MAX_HEAP_SIZE(self, funcgen, op):
        return ''


class RefcountingInfo:
    static_deallocator = None

from pypy.rlib.objectmodel import CDefinedIntSymbolic

class RefcountingGcPolicy(BasicGcPolicy):
    transformerclass = refcounting.RefcountingGCTransformer

    def common_gcheader_definition(self, defnode):
        if defnode.db.gctransformer is not None:
            HDR = defnode.db.gctransformer.HDR
            return [(name, HDR._flds[name]) for name in HDR._names]
        else:
            return []

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            gct = defnode.db.gctransformer
            hdr = gct.gcheaderbuilder.header_of_object(top_container(defnode.obj))
            HDR = gct.HDR
            return [getattr(hdr, fldname) for fldname in HDR._names]
        else:
            return []

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
    typename = 'void (@)(void *)'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, RttiStruct)
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

    # for MoreExactBoehmGcPolicy
    malloc_exact = False

class BoehmGcPolicy(BasicGcPolicy):
    transformerclass = boehm.BoehmGCTransformer

    def array_setup(self, arraydefnode):
        pass

    def struct_setup(self, structdefnode, rtti):
        pass

    def rtti_type(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode

    def gc_libraries(self):
        if sys.platform == 'win32':
            return ['gc_pypy']
        return ['gc']

    def pre_pre_gc_code(self):
        if sys.platform == "linux2":
            yield "#define _REENTRANT 1"
            yield "#define GC_LINUX_THREADS 1"
        if sys.platform != "win32":
            # GC_REDIRECT_TO_LOCAL is not supported on Win32 by gc6.8
            yield "#define GC_REDIRECT_TO_LOCAL 1"
        yield "#define GC_I_HIDE_POINTERS 1"
        yield '#include <gc/gc.h>'
        yield '#define USING_BOEHM_GC'

    def pre_gc_code(self):
        return []

    def gc_startup_code(self):
        if sys.platform == 'win32':
            pass # yield 'assert(GC_all_interior_pointers == 0);'
        else:
            yield 'GC_all_interior_pointers = 0;'
        yield 'GC_init();'

    def get_real_weakref_type(self):
        return boehm.WEAKLINK

    def convert_weakref_to(self, ptarget):
        return boehm.convert_weakref_to(ptarget)

    def OP_GC_FETCH_EXCEPTION(self, funcgen, op):
        result = funcgen.expr(op.result)
        return ('%s = RPyFetchExceptionValue();\n'
                'RPyClearException();') % (result, )

    def OP_GC_RESTORE_EXCEPTION(self, funcgen, op):
        argh = funcgen.expr(op.args[0])
        return 'if (%s != NULL) RPyRaiseException(RPYTHON_TYPE_OF_EXC_INST(%s), %s);' % (argh, argh, argh)

    def OP_GC__COLLECT(self, funcgen, op):
        return 'GC_gcollect(); GC_invoke_finalizers();'

    def OP_GC_SET_MAX_HEAP_SIZE(self, funcgen, op):
        nbytes = funcgen.expr(op.args[0])
        return 'GC_set_max_heap_size(%s);' % (nbytes,)

class BoehmGcRuntimeTypeInfo_OpaqueNode(ContainerNode):
    nodekind = 'boehm rtti'
    globalcontainer = True
    typename = 'char @'

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, RttiStruct)
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

class FrameworkGcRuntimeTypeInfo_OpaqueNode(BoehmGcRuntimeTypeInfo_OpaqueNode):
    nodekind = 'framework rtti'


class MoreExactBoehmGcPolicy(BoehmGcPolicy):
    """ policy to experiment with giving some layout information to boehm. Use
    new class to prevent breakage. """

    def __init__(self, db, thread_enabled=False):
        super(MoreExactBoehmGcPolicy, self).__init__(db, thread_enabled)
        self.exactly_typed_structs = {}

    def get_descr_name(self, defnode):
        # XXX somewhat illegal way of introducing a name
        return '%s__gc_descr__' % (defnode.name, )

    def pre_pre_gc_code(self):
        for line in super(MoreExactBoehmGcPolicy, self).pre_pre_gc_code():
            yield line
        yield "#include <gc/gc_typed.h>"

    def struct_setup(self, structdefnode, rtti):
        T = structdefnode.STRUCT
        if T._is_atomic():
            malloc_exact = False
        else:
            if T._is_varsize():
                malloc_exact = T._flds[T._arrayfld]._is_atomic()
            else:
                malloc_exact = True
        if malloc_exact:
            if structdefnode.gcinfo is None:
                structdefnode.gcinfo = BoehmInfo()
            structdefnode.gcinfo.malloc_exact = True
            self.exactly_typed_structs[structdefnode.STRUCT] = structdefnode

    def struct_after_definition(self, defnode):
        if defnode.gcinfo and defnode.gcinfo.malloc_exact:
            yield 'GC_descr %s;' % (self.get_descr_name(defnode), )

    def gc_startup_code(self):
        for line in super(MoreExactBoehmGcPolicy, self).gc_startup_code():
            yield line
        for TYPE, defnode in self.exactly_typed_structs.iteritems():
            T = defnode.gettype().replace("@", "")
            yield "{"
            yield "GC_word T_bitmap[GC_BITMAP_SIZE(%s)] = {0};" % (T, )
            for field in TYPE._flds:
                if getattr(TYPE, field) == lltype.Void:
                    continue
                yield "GC_set_bit(T_bitmap, GC_WORD_OFFSET(%s, %s));" % (
                    T, defnode.c_struct_field_name(field))
            yield "%s = GC_make_descriptor(T_bitmap, GC_WORD_LEN(%s));" % (
                self.get_descr_name(defnode), T)
            yield "}"


# to get an idea how it looks like with no refcount/gc at all

class NoneGcPolicy(BoehmGcPolicy):

    gc_libraries = RefcountingGcPolicy.gc_libraries.im_func
    gc_startup_code = RefcountingGcPolicy.gc_startup_code.im_func

    def pre_pre_gc_code(self):
        yield '#define USING_NO_GC'


class FrameworkGcPolicy(BasicGcPolicy):
    transformerclass = framework.FrameworkGCTransformer

    def struct_setup(self, structdefnode, rtti):
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            # make sure this is seen by the database early, i.e. before
            # finish_helpers() on the gctransformer
            self.db.get(destrptr)
            # the following, on the other hand, will only discover ll_finalizer
            # helpers.  The get() sees and records a delayed pointer.  It is
            # still important to see it so that it can be followed as soon as
            # the mixlevelannotator resolves it.
            gctransf = self.db.gctransformer
            fptr = gctransf.finalizer_funcptr_for_type(structdefnode.STRUCT)
            self.db.get(fptr)

    def array_setup(self, arraydefnode):
        pass

    def rtti_type(self):
        return FrameworkGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return FrameworkGcRuntimeTypeInfo_OpaqueNode

    def pre_pre_gc_code(self):
        yield '#define USING_FRAMEWORK_GC'

    def gc_startup_code(self):
        fnptr = self.db.gctransformer.frameworkgc_setup_ptr.value
        yield '%s();' % (self.db.get(fnptr),)

    def OP_GC_RELOAD_POSSIBLY_MOVED(self, funcgen, op):
        args = [funcgen.expr(v) for v in op.args]
        # XXX this more or less assumes mark-and-sweep gc
        return ''
        # proper return value for moving GCs:
        # %s = %s; /* for moving GCs */' % (args[1], args[0])

    def common_gcheader_definition(self, defnode):
        return defnode.db.gctransformer.gc_fields()

    def common_gcheader_initdata(self, defnode):
        o = top_container(defnode.obj)
        return defnode.db.gctransformer.gc_field_values_for(o)

class StacklessFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = stacklessframework.StacklessFrameworkGCTransformer
    requires_stackless = True


name_to_gcpolicy = {
    'boehm': BoehmGcPolicy,
    'exact_boehm': MoreExactBoehmGcPolicy,
    'ref': RefcountingGcPolicy,
    'none': NoneGcPolicy,
    'framework': FrameworkGcPolicy,
    'stacklessgc': StacklessFrameworkGcPolicy,
}


