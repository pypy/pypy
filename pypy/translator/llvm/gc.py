import sys
from pypy.rpython.lltypesystem.rstr import STR

from pypy.translator.llvm.log import log
log = log.gc

class GcPolicy:
    def __init__(self, db):
        raise Exception, 'GcPolicy should not be used directly'
    
    def genextern_code(self):
        return ''
    
    def gc_libraries(self):
        return []
    
    def pyrex_code(self):
        return ''    

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
        raise NotImplementedError, 'GcPolicy should not be used directly'

    def var_malloc(self, codewriter, targetvar, type_, node, len, atomic=False):
        raise NotImplementedError, 'GcPolicy should not be used directly'

    def new(db, gcpolicy=None):
        """ factory """
        gcpolicy = gcpolicy or 'boehm'
        
        # XXX would be nice to localise this sort of thing?
        import distutils.sysconfig
        from os.path import exists
        libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"  
        boehm_on_path = exists(libdir + '/libgc.so') or exists(libdir + '/libgc.a')
        if gcpolicy == 'boehm' and not boehm_on_path:
            log.gc.WARNING('warning: Boehm GC libary not found in /usr/lib, falling back on no gc')
            gcpolicy = 'raw'

        if gcpolicy == 'boehm':
            gcpolicy = BoehmGcPolicy(db)
        elif gcpolicy == 'ref':
            gcpolicy = RefcountingGcPolicy(db)
        elif gcpolicy in ('none', 'raw'):
            gcpolicy = RawGcPolicy(db)
        else:
            raise Exception, 'unknown gcpolicy: ' + str(gcpolicy)
        return gcpolicy
    new = staticmethod(new)


class RawGcPolicy(GcPolicy):
    def __init__(self, db):
        self.boehm = BoehmGcPolicy(db)

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False, exc_flag=False):
        return self.boehm.malloc(codewriter, targetvar, type_, size, atomic, exc_flag)

    def var_malloc(self, codewriter, targetvar, type_, node, len, atomic=False):
        return self.boehm.var_malloc(codewriter, targetvar, type_, node, len, atomic)

    def genextern_code(self):
        r = ''
        r += '#define __GC_STARTUP_CODE__\n'
        r += '#define __GC_SETUP_CODE__\n'
        r += 'char* pypy_malloc(int size)        { return calloc(1, size); }\n'
        r += 'char* pypy_malloc_atomic(int size) { return calloc(1, size); }\n'
        return r


class BoehmGcPolicy(GcPolicy):

    def __init__(self, db, exc_useringbuf=False):
        self.db = db
        self.n_malloced = 0
        self.exc_useringbuf = exc_useringbuf
        
    def genextern_code(self):
        r = '#include "boehm.h"\n'

        if self.exc_useringbuf:
            r += '#define __GC_SETUP_CODE__ ll_ringbuffer_initialise();\n'
        else:
            r += '#define __GC_SETUP_CODE__\n'
        return r
    
    def gc_libraries(self):
        return ['gc', 'pthread'] # XXX on windows?

    def pyrex_code(self):
        return '''
cdef extern int GC_get_heap_size()

def GC_get_heap_size_wrapper():
    return GC_get_heap_size()
'''

    def get_count(self, inc=False):
        if inc:
            self.n_malloced += 1
        return '_%d' % self.n_malloced

    def _malloc(self, codewriter, targetvar, size=1, atomic=False,
                exc_flag=False):
        """ assumes malloc of word size """
        # XXX Boehm aligns on 8 byte boundaries
    	#if sys.platform == 'linux2' and sys.maxint == 2**63-1:
        #    boundary_size = 8
	#else:
        #    boundary_size = 0
        boundary_size = 0

        word = self.db.get_machine_word()
        uword = self.db.get_machine_uword()

        if self.exc_useringbuf and exc_flag:
            fnname = '%pypy_' + self.ringbuf_malloc_name
            atomic = False
        else:
            fnname = '%pypy_malloc' + (atomic and '_atomic' or '')

        # malloc_size is unsigned right now
        sizei = '%malloc_sizei' + self.get_count()        
        codewriter.cast(sizei, uword, size, word)
        codewriter.call(targetvar, 'sbyte*', fnname, [word], [sizei])
        
        if atomic:
            codewriter.call(None, 'void', '%llvm.memset',
                            ['sbyte*', 'ubyte', uword, uword],
                            [targetvar, 0, size, boundary_size],
                            cconv='ccc')        

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False,
               exc_flag=False):
        uword = self.db.get_machine_uword()
        malloc_ptr = '%malloc_ptr' + self.get_count(True)
        malloc_size = '%malloc_size' + self.get_count()
        malloc_sizeu = '%malloc_sizeu' + self.get_count()
        
        codewriter.getelementptr(malloc_size, type_, 'null',
                                 [(uword, size)], getptr=False)
        codewriter.cast(malloc_sizeu, type_, malloc_size, uword)
        self._malloc(codewriter, malloc_ptr, malloc_sizeu, atomic, exc_flag)
        codewriter.cast(targetvar, 'sbyte*', malloc_ptr, type_)            

    def var_malloc(self, codewriter, targetvar,
                   type_, node, len, atomic=False):

        word = lentype = self.db.get_machine_word()
        uword = self.db.get_machine_uword()
        malloc_ptr = '%malloc_ptr' + self.get_count(True)
        malloc_size = '%malloc_size' + self.get_count()
        malloc_sizeu = '%malloc_sizeu' + self.get_count()
        actuallen = '%actuallen' + self.get_count()
        arraylength = '%arraylength' + self.get_count()
        
        ARRAY, indices_to_array = node.var_malloc_info()
        
        #varsized arrays and structs look like this: 
        #Array: {int length , elemtype*}
        #Struct: {...., Array}
        
        # the following indices access the last element in the array
        elemtype = self.db.repr_type(ARRAY.OF)
        word = lentype = self.db.get_machine_word()
        uword = self.db.get_machine_uword()
        
        # need room for NUL terminator
        if ARRAY is STR.chars:
            codewriter.binaryop('add', actuallen, lentype, len, 1)
        else:
            codewriter.cast(actuallen, lentype, len, lentype)
            
        elemindices = list(indices_to_array)
        elemindices += [('uint', 1), (lentype, actuallen)]
        codewriter.getelementptr(malloc_size, type_, 'null', elemindices) 
        codewriter.cast(malloc_sizeu, elemtype + '*', malloc_size, uword)
        
        self._malloc(codewriter, malloc_ptr, malloc_sizeu, atomic=atomic)

        indices_to_arraylength = tuple(indices_to_array) + (('uint', 0),)

        codewriter.cast(targetvar, 'sbyte*', malloc_ptr, type_)

        # the following accesses the length field of the array 
        codewriter.getelementptr(arraylength, type_, 
                                 targetvar,  indices_to_arraylength)
        codewriter.store(lentype, len, arraylength)


class RefcountingGcPolicy(GcPolicy):
    def __init__(self, db):
        raise NotImplementedError, 'RefcountingGcPolicy'
