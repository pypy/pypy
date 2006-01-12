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

    # malloc is not an codewriter specific thing
    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
        # XXX _indent & test
        codewriter._indent('%(targetvar)s = malloc %(type_)s, uint %(s)s' % locals())
    
    def write_constructor(self, codewriter, ref, constructor_decl, ARRAY, 
                          indices_to_array=(), atomic=False, is_str=False):


        #varsized arrays and structs look like this: 
        #Array: {int length , elemtype*}
        #Struct: {...., Array}

        # the following indices access the last element in the array
        elemtype = self.db.repr_type(ARRAY.OF)
        word = lentype = self.db.get_machine_word()
        uword = self.db.get_machine_uword()

        codewriter.openfunc(constructor_decl)    

        # Need room for NUL terminator
        if ARRAY is STR.chars:
            codewriter.binaryop("add", "%actuallen", lentype, "%len", 1)
        else:
            codewriter.cast("%actuallen", lentype, "%len", lentype)

        elemindices = list(indices_to_array)
        elemindices += [("uint", 1), (lentype, "%actuallen")]
        codewriter.getelementptr("%size", ref + "*", "null", elemindices) 
        codewriter.cast("%usize", elemtype + "*", "%size", uword)
        self.malloc(codewriter, "%ptr", "sbyte*", "%usize", atomic=atomic)
        codewriter.cast("%result", "sbyte*", "%ptr", ref + "*")

        indices_to_arraylength = tuple(indices_to_array) + (("uint", 0),)

        # the following accesses the length field of the array 
        codewriter.getelementptr("%arraylength", ref + "*", 
                                 "%result", 
                                 indices_to_arraylength)
        codewriter.store(lentype, "%len", "%arraylength")

        #if is_str:
        #    indices_to_hash = (("uint", 0),)
        #    codewriter.getelementptr("%ptrhash", ref + "*", 
        #                             "%result", 
        #                             indices_to_hash)
        #    codewriter.store("int", "0", "%ptrhash")


        #if ARRAY is STR.chars:
        #    codewriter.getelementptr("%ptrendofchar", ref + "*", 
        #                             "%result", 
        #                             elemindices)
        #    codewriter.store(elemtype, "0", "%ptrendofchar")

        codewriter.ret(ref + "*", "%result")
        codewriter.closefunc()

    def pyrex_code(self):
        return ''

    def new(db, gcpolicy=None):  #factory
        gcpolicy = gcpolicy or 'boehm'

        import distutils.sysconfig
        from os.path import exists
        libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"  
        boehm_on_path = exists(libdir + '/libgc.so') or exists(libdir + '/libgc.a')
        if gcpolicy == 'boehm' and not boehm_on_path:
            log.gc.WARNING('warning: Boehm GC libary not found in /usr/lib, falling back on no gc')
            gcpolicy = 'none'

        if gcpolicy == 'boehm':
            gcpolicy = BoehmGcPolicy(db)
        elif gcpolicy == 'ref':
            gcpolicy = RefcountingGcPolicy(db)
        elif gcpolicy == 'none':
            gcpolicy = NoneGcPolicy(db)
        else:
            raise Exception, 'unknown gcpolicy: ' + str(gcpolicy)
        return gcpolicy
    new = staticmethod(new)


class NoneGcPolicy(GcPolicy):
    def __init__(self, db):
        self.db = db


class BoehmGcPolicy(GcPolicy):
    def __init__(self, db):
        self.db = db
        self.n_malloced = 0

    def genextern_code(self):
        return '#include "boehm.h"'

    def gc_libraries(self):
        return ['gc', 'pthread'] # XXX on windows?


    def malloc(self, codewriter, targetvar, type_, size=1, atomic=False):
        is_atomic = atomic
        uword = self.db.get_machine_uword()
        s = str(size)
        self.n_malloced += 1
        cnt = '.%d' % self.n_malloced
        atomic = is_atomic and '_atomic' or ''
        t = '''
%%malloc_Size%(cnt)s  = getelementptr %(type_)s null, %(uword)s %(s)s
%%malloc_SizeU%(cnt)s = cast %(type_)s %%malloc_Size%(cnt)s to %(uword)s
%%malloc_Ptr%(cnt)s   = call fastcc sbyte* %%pypy_malloc%(atomic)s(%(uword)s %%malloc_SizeU%(cnt)s)
%(targetvar)s = cast sbyte* %%malloc_Ptr%(cnt)s to %(type_)s
''' % locals()

        if is_atomic:
            t += '''
        call ccc void %%llvm.memset(sbyte* %%malloc_Ptr%(cnt)s, ubyte 0, %(uword)s %%malloc_SizeU%(cnt)s, uint 0)
        ''' % locals()
        codewriter.write_lines(t)

    def pyrex_code(self):
        return '''
cdef extern int GC_get_heap_size()

def GC_get_heap_size_wrapper():
    return GC_get_heap_size()
'''


class RefcountingGcPolicy(GcPolicy):
    def __init__(self):
        raise NotImplementedError, 'RefcountingGcPolicy'
