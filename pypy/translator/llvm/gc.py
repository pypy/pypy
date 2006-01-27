import sys
from pypy.rpython.rstr import STR

from pypy.translator.llvm.log import log
log = log.gc

class GcPolicy:
    def __init__(self, db):
        raise Exception, 'GcPolicy should not be used directly'
    
    def genextern_code(self):
        return ""
    
    def gc_libraries(self):
        return []
    
    def pyrex_code(self):
        return ''    

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
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
        elif gcpolicy == 'raw':
            gcpolicy = RawGcPolicy(db)
        else:
            raise Exception, 'unknown gcpolicy: ' + str(gcpolicy)
        return gcpolicy
    new = staticmethod(new)

class RawGcPolicy(GcPolicy):
    def __init__(self, db):
        self.db = db

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
        codewriter.malloc(targetvar, type_, size)
        #XXX memset
        
class BoehmGcPolicy(GcPolicy):
    def __init__(self, db):
        self.db = db
        self.n_malloced = 0
        
    def genextern_code(self):
        return '#include "boehm.h"'
    
    def gc_libraries(self):
        return ['gc', 'pthread'] # XXX on windows?

    def pyrex_code(self):
        return '''
cdef extern int GC_get_heap_size()

def GC_get_heap_size_wrapper():
    return GC_get_heap_size()
'''

    def _malloc(self, codewriter, targetvar, size=1, atomic=False):
        """ assumes malloc of word size """
        # XXX Boehm aligns on 8 byte boundaries
    	if sys.platform == 'linux2' and sys.maxint == 2**63-1:
            boundary_size = 8
	else:
            boundary_size = 0

        uword = self.db.get_machine_uword()
        fnname = '%pypy_malloc' + (atomic and '_atomic' or '')
        codewriter.call(targetvar, 'sbyte*', fnname, [uword], [size])
        
        if atomic:
            codewriter.call(None, 'void', '%llvm.memset',
                            ['sbyte*', 'ubyte', uword, uword],
                            [targetvar, 0, size, boundary_size],
                            cconv='ccc')        

    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
        uword = self.db.get_machine_uword()
        self.n_malloced += 1
        cnt = '_%d' % self.n_malloced
        malloc_ptr = '%malloc_ptr' + cnt
        malloc_size = '%malloc_size' + cnt
        malloc_sizeu = '%malloc_sizeu' + cnt
        
        codewriter.getelementptr(malloc_size, type_, 'null',
                                 [(uword, size)], getptr=False)
        codewriter.cast(malloc_sizeu, type_, malloc_size, uword)
        self._malloc(codewriter, malloc_ptr, malloc_sizeu, atomic)
        codewriter.cast(targetvar, 'sbyte*', malloc_ptr, type_)            

    def var_malloc(self, codewriter, targetvar,
                   type_, node, len, atomic=False):

        word = lentype = self.db.get_machine_word()
        uword = self.db.get_machine_uword()
        self.n_malloced += 1
        cnt = '_%d' % self.n_malloced
        malloc_ptr = '%malloc_ptr' + cnt
        malloc_size = '%malloc_size' + cnt
        malloc_sizeu = '%malloc_sizeu' + cnt
        actuallen = '%actuallen' + cnt
        arraylength = '%arraylength' + cnt
        
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
