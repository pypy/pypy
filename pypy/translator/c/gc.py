import sys
from pypy.objspace.flow.model import Constant
from pypy.translator.c.support import cdecl
from pypy.translator.c.node import ContainerNode
from pypy.rpython.lltypesystem.lltype import \
     typeOf, Ptr, ContainerType, RttiStruct, \
     RuntimeTypeInfo, getRuntimeTypeInfo, top_container
from pypy.rpython.memory.gctransform import \
     refcounting, boehm, framework, asmgcroot
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.tool.cbuild import ExternalCompilationInfo

class BasicGcPolicy(object):
    requires_stackless = False
    stores_hash_at_the_end = False

    def __init__(self, db, thread_enabled=False):
        self.db = db
        self.thread_enabled = thread_enabled

    def common_gcheader_definition(self, defnode):
        if defnode.db.gctransformer is not None:
            return defnode.db.gctransformer.HDR
        return None

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            raise NotImplementedError
        return None

    def struct_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def struct_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def array_gcheader_definition(self, defnode):
        return self.common_gcheader_definition(defnode)

    def array_gcheader_initdata(self, defnode):
        return self.common_gcheader_initdata(defnode)

    def compilation_info(self):
        if not self.db:
            return ExternalCompilationInfo()

        gct = self.db.gctransformer
        return ExternalCompilationInfo(
            pre_include_bits=['/* using %s */' % (gct.__class__.__name__,),
                              '#define MALLOC_ZERO_FILLED %d' % (gct.malloc_zero_filled,),
                              ],
            post_include_bits=['typedef void *GC_hidden_pointer;']
            )

    def get_prebuilt_hash(self, obj):
        return None

    def need_no_typeptr(self):
        return False

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

    def OP_GC_THREAD_PREPARE(self, funcgen, op):
        return ''

    def OP_GC_THREAD_RUN(self, funcgen, op):
        return ''

    def OP_GC_THREAD_START(self, funcgen, op):
        return ''

    def OP_GC_THREAD_DIE(self, funcgen, op):
        return ''

    def OP_GC_THREAD_BEFORE_FORK(self, funcgen, op):
        return '%s = NULL;' % funcgen.expr(op.result)

    def OP_GC_THREAD_AFTER_FORK(self, funcgen, op):
        return ''

    def OP_GC_ASSUME_YOUNG_POINTERS(self, funcgen, op):
        return ''

    def OP_GC_STACK_BOTTOM(self, funcgen, op):
        return ''


class RefcountingInfo:
    static_deallocator = None

from pypy.rlib.objectmodel import CDefinedIntSymbolic

class RefcountingGcPolicy(BasicGcPolicy):
    transformerclass = refcounting.RefcountingGCTransformer

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            gct = defnode.db.gctransformer
            top = top_container(defnode.obj)
            return gct.gcheaderbuilder.header_of_object(top)._obj
        return None

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

    def OP_GC__COLLECT(self, funcgen, op):
        return ''

    def OP_GC__DISABLE_FINALIZERS(self, funcgen, op):
        return ''

    def OP_GC__ENABLE_FINALIZERS(self, funcgen, op):
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

    def getptrname(self):
        return '((void (*)(void *)) %s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []



class BoehmInfo:
    finalizer = None


class BoehmGcPolicy(BasicGcPolicy):
    transformerclass = boehm.BoehmGCTransformer

    def common_gcheader_initdata(self, defnode):
        if defnode.db.gctransformer is not None:
            hdr = lltype.malloc(defnode.db.gctransformer.HDR, immortal=True)
            hdr.hash = lltype.identityhash_nocache(defnode.obj._as_ptr())
            return hdr._obj
        return None

    def array_setup(self, arraydefnode):
        pass

    def struct_setup(self, structdefnode, rtti):
        pass

    def rtti_type(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode.typename

    def rtti_node_factory(self):
        return BoehmGcRuntimeTypeInfo_OpaqueNode

    def compilation_info(self):
        eci = BasicGcPolicy.compilation_info(self)

        from pypy.rpython.tool.rffi_platform import configure_boehm
        eci = eci.merge(configure_boehm())

        pre_include_bits = []
        if sys.platform.startswith('linux'):
            pre_include_bits += ["#define _REENTRANT 1",
                                 "#define GC_LINUX_THREADS 1"]
        if sys.platform != "win32":
            # GC_REDIRECT_TO_LOCAL is not supported on Win32 by gc6.8
            pre_include_bits += ["#define GC_REDIRECT_TO_LOCAL 1"]

        eci = eci.merge(ExternalCompilationInfo(
            pre_include_bits=pre_include_bits,
            post_include_bits=['#define USING_BOEHM_GC'],
            ))

        return eci

    def gc_startup_code(self):
        if sys.platform == 'win32':
            pass # yield 'assert(GC_all_interior_pointers == 0);'
        else:
            yield 'GC_all_interior_pointers = 0;'
        yield 'boehm_gc_startup_code();'

    def get_real_weakref_type(self):
        return boehm.WEAKLINK

    def convert_weakref_to(self, ptarget):
        return boehm.convert_weakref_to(ptarget)

    def OP_GC__COLLECT(self, funcgen, op):
        return 'GC_gcollect();'

    def OP_GC_SET_MAX_HEAP_SIZE(self, funcgen, op):
        nbytes = funcgen.expr(op.args[0])
        return 'GC_set_max_heap_size(%s);' % (nbytes,)

    def GC_KEEPALIVE(self, funcgen, v):
        return 'pypy_asm_keepalive(%s);' % funcgen.expr(v)

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

    def getptrname(self):
        return '(&%s)' % (self.name,)

    def enum_dependencies(self):
        return []

    def implementation(self):
        yield 'char %s  /* uninitialized */;' % self.name

class FrameworkGcRuntimeTypeInfo_OpaqueNode(BoehmGcRuntimeTypeInfo_OpaqueNode):
    nodekind = 'framework rtti'


# to get an idea how it looks like with no refcount/gc at all

class NoneGcPolicy(BoehmGcPolicy):

    gc_startup_code = RefcountingGcPolicy.gc_startup_code.im_func

    def compilation_info(self):
        eci = BasicGcPolicy.compilation_info(self)
        eci = eci.merge(ExternalCompilationInfo(
            post_include_bits=['#define USING_NO_GC_AT_ALL'],
            ))
        return eci


class FrameworkGcPolicy(BasicGcPolicy):
    transformerclass = framework.FrameworkGCTransformer
    stores_hash_at_the_end = True

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

    def gc_startup_code(self):
        fnptr = self.db.gctransformer.frameworkgc_setup_ptr.value
        yield '%s();' % (self.db.get(fnptr),)

    def get_real_weakref_type(self):
        return framework.WEAKREF

    def convert_weakref_to(self, ptarget):
        return framework.convert_weakref_to(ptarget)

    def OP_GC_RELOAD_POSSIBLY_MOVED(self, funcgen, op):
        if isinstance(op.args[1], Constant):
            return '/* %s */' % (op,)
        else:
            args = [funcgen.expr(v) for v in op.args]
            return '%s = %s; /* for moving GCs */' % (args[1], args[0])

    def common_gcheader_initdata(self, defnode):
        o = top_container(defnode.obj)
        needs_hash = self.get_prebuilt_hash(o) is not None
        hdr = defnode.db.gctransformer.gc_header_for(o, needs_hash)
        return hdr._obj

    def get_prebuilt_hash(self, obj):
        # for prebuilt objects that need to have their hash stored and
        # restored.  Note that only structures that are StructNodes all
        # the way have their hash stored (and not e.g. structs with var-
        # sized arrays at the end).  'obj' must be the top_container.
        TYPE = typeOf(obj)
        if not isinstance(TYPE, lltype.GcStruct):
            return None
        if TYPE._is_varsize():
            return None
        return getattr(obj, '_hash_cache_', None)

    def need_no_typeptr(self):
        config = self.db.translator.config
        return config.translation.gcremovetypeptr

    def OP_GC_GETTYPEPTR_GROUP(self, funcgen, op):
        # expands to a number of steps, as per rpython/lltypesystem/opimpl.py,
        # all implemented by a single call to a C macro.
        [v_obj, c_grpptr, c_skipoffset, c_vtableinfo] = op.args
        typename = funcgen.db.gettype(op.result.concretetype)
        tid_field = c_vtableinfo.value[2]
        # Fish out the C name of the tid field.
        HDR = self.db.gctransformer.HDR
        hdr_node = self.db.gettypedefnode(HDR)
        fieldname = hdr_node.c_struct_field_name(tid_field)
        return (
        '%s = (%s)_OP_GET_NEXT_GROUP_MEMBER(%s, (pypy_halfword_t)%s->'
            '_gcheader.%s, %s);'
            % (funcgen.expr(op.result),
               cdecl(typename, ''),
               funcgen.expr(c_grpptr),
               funcgen.expr(v_obj),
               fieldname,
               funcgen.expr(c_skipoffset)))

class AsmGcRootFrameworkGcPolicy(FrameworkGcPolicy):
    transformerclass = asmgcroot.AsmGcRootFrameworkGCTransformer

    def GC_KEEPALIVE(self, funcgen, v):
        return 'pypy_asm_keepalive(%s);' % funcgen.expr(v)

    def OP_GC_STACK_BOTTOM(self, funcgen, op):
        return 'pypy_asm_stack_bottom();'


name_to_gcpolicy = {
    'boehm': BoehmGcPolicy,
    'ref': RefcountingGcPolicy,
    'none': NoneGcPolicy,
    'framework': FrameworkGcPolicy,
    'framework+asmgcroot': AsmGcRootFrameworkGcPolicy,
}


