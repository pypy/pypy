import sys
from pypy.rpython.lltypesystem.rstr import STR
from pypy.translator.c import gc

from pypy.translator.llvm.log import log
log = log.gc

from pypy.translator.llvm.buildllvm import postfix

def have_boehm():
    import distutils.sysconfig
    from os.path import exists
    libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"  
    return exists(libdir + '/libgc.so') or exists(libdir + '/libgc.a')

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

    def op_fetch_exception(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'

    def op_restore_exception(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'

    def op_collect(self, codewriter, opr):
        raise Exception, 'GcPolicy should not be used directly'

    def new(db, gcpolicy=None):
    #    """ factory """
        if gcpolicy == 'boehm':
            # XXX would be nice to localise this sort of thing?
            #assert have_boehm(), 'warning: Boehm GC libary not found in /usr/lib'
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
        uword = self.db.get_machine_uword()
        boundary_size = 0

        # malloc_size is unsigned right now
        codewriter.malloc(targetvar, "sbyte", size)
        codewriter.call(None, 'void', '%llvm.memset' + postfix(),
                        ['sbyte*', 'ubyte', uword, uword],
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
        uword = self.db.get_machine_uword()

        fnname = '%pypy_malloc' + (atomic and '_atomic' or '')

##        XXX (arigo) disabled the ring buffer for comparison purposes
##        XXX until we know if it's a valid optimization or not

##        if self.exc_useringbuf and exc_flag:
##            fnname += '_ringbuffer'
##            # dont clear the ringbuffer data
##            atomic = False 

        # malloc_size is unsigned right now
        sizeu = '%malloc_sizeu' + self.get_count()        
        codewriter.cast(sizeu, word, size, uword)
        codewriter.call(targetvar, 'sbyte*', fnname, [word], [size])

        if atomic:
            codewriter.call(None, 'void', '%llvm.memset' + postfix(),
                            ['sbyte*', 'ubyte', uword, uword],
                            [targetvar, 0, sizeu, boundary_size],
                            cconv='ccc')        


    def op__collect(self, codewriter, opr):
        codewriter.call(opr.retref, opr.rettype, "%pypy_gc__collect",
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
        # XXX
        # This is not finished: we must call the gc init function!
        r  = ''
        r += '#define __GC_STARTUP_CODE__\n'
        r += '#define __GC_SETUP_CODE__\n'
        return r

    def gc_libraries(self):
        return ['pthread']
