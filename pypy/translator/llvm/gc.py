class GcPolicy:
    def __init__(self):
        raise Exception, 'GcPolicy should not be used directly'

    def gc_libraries(self):
        return []

    def llvm_code(self):
        return '''
internal fastcc sbyte* %gc_malloc(uint %n) {
    %nn  = cast uint %n to uint
    %ptr = malloc sbyte, uint %nn
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %nn  = cast uint %n to uint
    %ptr = malloc sbyte, uint %nn
    ret sbyte* %ptr
}
'''

    def pyrex_code(self):
        return ''

    def new(gcpolicy=None):  #factory
        if gcpolicy is None or gcpolicy == 'boehm':
            from os.path import exists
            boehm_on_path = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')
            if not boehm_on_path:
                raise Exception, 'Boehm GC libary not found in /usr/lib'
            from pypy.translator.llvm.gc import BoehmGcPolicy
            gcpolicy = BoehmGcPolicy()
        elif gcpolicy == 'ref':
            from pypy.translator.llvm.gc import RefcountingGcPolicy
            gcpolicy = RefcountingGcPolicy()
        elif gcpolicy == 'none':
            from pypy.translator.llvm.gc import NoneGcPolicy
            gcpolicy = NoneGcPolicy()
        else:
            raise Exception, 'unknown gcpolicy: ' + str(gcpolicy)
        return gcpolicy
    new = staticmethod(new)


class NoneGcPolicy(GcPolicy):
    def __init__(self):
        pass


class BoehmGcPolicy(GcPolicy):
    def __init__(self):
        pass

    def gc_libraries(self):
        return ['gc'] # xxx on windows?

    def llvm_code(self):
        return '''
declare ccc sbyte* %GC_malloc(uint)
declare ccc sbyte* %GC_malloc_atomic(uint)

internal fastcc sbyte* %gc_malloc(uint %n) {
    %ptr = call ccc sbyte* %GC_malloc(uint %n)
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = call ccc sbyte* %GC_malloc_atomic(uint %n)
    ret sbyte* %ptr
}
'''

    def pyrex_code(self):
        return '''
cdef extern int GC_get_heap_size()

def GC_get_heap_size_wrapper():
    return GC_get_heap_size()
'''


class RefcountingGcPolicy(GcPolicy):
    def __init__(self):
        raise NotImplementedError, 'RefcountingGcPolicy'
