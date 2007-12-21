import sys
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.lltypesystem import lltype
from pypy.translator.c import gc

from pypy.translator.llvm.log import log
log = log.gc

from pypy.translator.llvm.buildllvm import postfix

class GcPolicy:
    n_malloced = 0
    def __init__(self, db):
        raise Exception, 'GcPolicy should not be used directly'

    def setup(self):
        pass
    
    def genextern_code(self):
        return ''

    def gcheader_definition(self, TYPE):
        return []

    def gcheader_initdata(self, container):
        return []
    
    def gc_libraries(self):
        return []

    def get_count(self, inc=False):
        if inc:
            self.n_malloced = self.n_malloced + 1
        return '_%d' % self.n_malloced

    def _zeromalloc(self, codewriter, targetvar, size=1, atomic=False,
                    exc_flag=False):
        raise NotImplementedError, 'GcPolicy should not be used directly'

    def op_call_rtti_destructor(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'
     
    def op_free(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'

    def op_collect(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'

    def op_set_max_heap_size(self, codewriter, opr):
        pass

    def new(db, config):
        gcpolicy = config.translation.gctransformer
        if gcpolicy == 'boehm':
            gcpolicy = BoehmGcPolicy(db)
        elif gcpolicy == 'ref':
            gcpolicy = RefcountingGcPolicy(db)
        elif gcpolicy in ('none', 'raw'):
            gcpolicy = RawGcPolicy(db)
        elif gcpolicy == 'framework':
            gcpolicy = FrameworkGcPolicy(db)
        else:
            raise Exception, 'unknown gcpolicy: ' + str(gcpolicy)
        return gcpolicy
    new = staticmethod(new)


class RawGcPolicy(GcPolicy):
    def __init__(self, db):
        self.db = db

    def genextern_code(self):
        r  = ''
        r += '#define __GC_STARTUP_CODE__\n'
        r += '#define __GC_SETUP_CODE__\n'
        r += 'char* pypy_malloc(int size)        { return calloc(1, size); }\n'
        r += 'char* pypy_malloc_atomic(int size) { return calloc(1, size); }\n'
        return r

    def gc_libraries(self):
        return ['pthread']

    def _zeromalloc(self, codewriter, targetvar, size=1, atomic=False,
                    exc_flag=False):
        """ assumes malloc of word size """
        XXX
        word = self.db.get_machine_word()
        boundary_size = 0

        # malloc_size is unsigned right now
        codewriter.malloc(targetvar, "i8", size)
        codewriter.call(None, 'void', '@llvm.memset' + postfix(),
                        ['i8*', 'i8', word, word],
                        [targetvar, 0, size, boundary_size])

class BoehmGcPolicy(GcPolicy):

    def __init__(self, db, exc_useringbuf=True):
        self.db = db
        # XXX a config option...
        self.exc_useringbuf = exc_useringbuf
        
    def genextern_code(self):
        r  = ''
        r += '#include "boehm.h"\n'
        r += '#define __GC_SETUP_CODE__\n'
        return r
    
    def gc_libraries(self):
        return ['gc', 'pthread']

    def get_real_weakref_type(self):
        from pypy.rpython.memory.gctransform import boehm
        return boehm.WEAKLINK

    def _zeromalloc(self, codewriter, targetvar, size=1, atomic=False,
                    exc_flag=False):
        """ assumes malloc of word size """
        boundary_size = 0
        word = self.db.get_machine_word()
        fnname = '@pypy_malloc' + (atomic and '_atomic' or '')

##        XXX (arigo) disabled the ring buffer for comparison purposes
##        XXX until we know if it's a valid optimization or not

##        if self.exc_useringbuf and exc_flag:
##            fnname += '_ringbuffer'
##            # dont clear the ringbuffer data
##            atomic = False 

        codewriter.call(targetvar, 'i8*', fnname, [word], [size])

        if atomic:
            codewriter.call(None, 'void', '@llvm.memset' + postfix(),
                            ['i8*', 'i8', word, word],
                            [targetvar, 0, size, boundary_size])


    def op__collect(self, codewriter, opr):
        codewriter.call(opr.retref, opr.rettype, "@pypy_gc__collect",
                        opr.argtypes, opr.argrefs)

class RefcountingGcPolicy(RawGcPolicy):

    def __init__(self, db, exc_useringbuf=True):
        self.db = db

    def op_call_rtti_destructor(self, codewriter, opr):
        log.WARNING("skipping op_call_rtti_destructor")
        
    def op_free(self, codewriter, opr):
        assert opr.rettype == 'void' and len(opr.argtypes) == 1
        codewriter.free(opr.argtypes[0], opr.argrefs[0])

class FrameworkGcPolicy(GcPolicy):

    def __init__(self, db):
        self.db = db

    def setup(self):
        c_fnptr = self.db.gctransformer.frameworkgc_setup_ptr
        self.db.prepare_arg(c_fnptr)

    def genextern_code(self):
        fnptr = self.db.gctransformer.frameworkgc_setup_ptr.value
        fnnode = self.db.obj2node[fnptr._obj]
        r = 'void %s(void);  /* forward declaration */\n' % (fnnode.name[1:],)
        r += '#define __GC_STARTUP_CODE__ %s();\n' % (fnnode.name[1:],)
        r += '#define __GC_SETUP_CODE__\n'
        return r

    def gcheader_definition(self, TYPE):
        if needs_gcheader(TYPE):
            return self.db.gctransformer.gc_fields()
        else:
            return []

    def gcheader_initdata(self, container):
        if needs_gcheader(container._TYPE):
            o = lltype.top_container(container)
            return self.db.gctransformer.gc_field_values_for(o)
        else:
            return []

    def gc_libraries(self):
        return ['pthread']

    def get_real_weakref_type(self):
        from pypy.rpython.memory.gctransform import framework
        return framework.WEAKREF


def needs_gcheader(T):
    if not isinstance(T, lltype.ContainerType):
        return False
    if T._gckind != 'gc':
        return False
    if isinstance(T, lltype.GcStruct):
        if T._first_struct() != (None, None):
            return False   # gcheader already in the first field
    return True
