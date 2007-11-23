import sys
from pypy.rpython.lltypesystem.rstr import STR
from pypy.translator.c import gc

from pypy.translator.llvm.log import log
log = log.gc

from pypy.translator.llvm.buildllvm import postfix

class GcPolicy:
    n_malloced = 0
    def __init__(self, db):
        raise Exception, 'GcPolicy should not be used directly'
    
    def genextern_code(self):
        return ''
    
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

    def new(db, gcpolicy=None):
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
        # XXX uses own cconv
        codewriter.call(None, 'void', '@llvm.memset' + postfix(),
                        ['i8*', 'i8', word, word],
                        [targetvar, 0, size, boundary_size],
                        cconv='ccc')               

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
            # XXX uses own cconv
            codewriter.call(None, 'void', '@llvm.memset' + postfix(),
                            ['i8*', 'i8', word, word],
                            [targetvar, 0, size, boundary_size],
                            cconv='ccc')        


    def op_set_max_heap_size(self, codewriter, opr):
        pass

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

    def genextern_code(self):
        r  = ''
        r += '#define __GC_STARTUP_CODE__\n'
        r += '#define __GC_SETUP_CODE__\n'
        return r

    def gc_libraries(self):
        return ['pthread']
