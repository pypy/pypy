import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("llvm")
log.setconsumer("llvm", ansi_log)


class GcPolicy:
    def __init__(self):
        raise Exception, 'GcPolicy should not be used directly'

    def gc_libraries(self):
        return []

    def declarations(self):
        return ''

    def malloc(self, targetvar, type_, size, is_atomic, word, uword):
        s = str(size)
        return '%(targetvar)s = malloc %(type_)s, uint %(s)s' % locals()

    def pyrex_code(self):
        return ''

    def new(gcpolicy=None):  #factory
        gcpolicy = gcpolicy or 'boehm'
        
        from os.path import exists
        boehm_on_path = exists('/usr/lib/libgc.so') or exists('/usr/lib/libgc.a')
        if gcpolicy == 'boehm' and not boehm_on_path:
            log.gc.WARNING('warning: Boehm GC libary not found in /usr/lib, falling back on no gc')
            gcpolicy = 'none'

        if gcpolicy == 'boehm':
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
        self.n_malloced = 0

    def gc_libraries(self):
        return ['gc'] # xxx on windows?

    def declarations(self):
        return '''
declare ccc sbyte* %GC_malloc(uint)
declare ccc sbyte* %GC_malloc_atomic(uint)
%GC_all_interior_pointers = external global int
'''

    def malloc(self, targetvar, type_, size, is_atomic, word, uword):
        s = str(size)
        self.n_malloced += 1
        cnt = '.%d' % self.n_malloced
        atomic = is_atomic and '_atomic' or ''
        t = '''
%%malloc.Size%(cnt)s  = getelementptr %(type_)s* null, %(uword)s %(s)s
%%malloc.SizeU%(cnt)s = cast %(type_)s* %%malloc.Size%(cnt)s to %(uword)s
%%malloc.Ptr%(cnt)s   = call ccc sbyte* %%GC_malloc%(atomic)s(%(uword)s %%malloc.SizeU%(cnt)s)
%(targetvar)s = cast sbyte* %%malloc.Ptr%(cnt)s to %(type_)s*
''' % locals()
        if is_atomic:
            t += '''
call ccc void %%llvm.memset(sbyte* %%malloc.Ptr%(cnt)s, ubyte 0, uint %%malloc.SizeU%(cnt)s, uint 0)
''' % locals()
        return t

    def pyrex_code(self):
        return '''
cdef extern int GC_get_heap_size()

def GC_get_heap_size_wrapper():
    return GC_get_heap_size()
'''


class RefcountingGcPolicy(GcPolicy):
    def __init__(self):
        raise NotImplementedError, 'RefcountingGcPolicy'
