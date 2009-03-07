
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rlib.objectmodel import we_are_translated
from pypy.translator.c.test.test_genc import compile
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.metainterp.history import log, ConstAddr
import ctypes
import py

GC_MALLOC = lltype.Ptr(lltype.FuncType([lltype.Signed], llmemory.Address))

def gc_malloc(size):
    return llop.call_boehm_gc_alloc(llmemory.Address, size)

def gc_malloc_fnaddr():
    """Returns the address of the Boehm 'malloc' function."""
    if we_are_translated():
        gc_malloc_ptr = llhelper(GC_MALLOC, gc_malloc)
        return lltype.cast_ptr_to_int(gc_malloc_ptr)
    else:
        try:
            from ctypes import cast, c_void_p, util
            path = util.find_library('gc')
            if path is None:
                raise ImportError("Boehm (libgc) not found")
            boehmlib = ctypes.cdll.LoadLibrary(path)
        except ImportError, e:
            import py
            py.test.skip(str(e))
        else:
            GC_malloc = boehmlib.GC_malloc
            return cast(GC_malloc, c_void_p).value

def c_meta_interp(function, args, **kwds):
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import WarmRunnerDesc
    from pypy.jit.backend.x86.runner import CPU386
    from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.annotation import model as annmodel
    
    for arg in args:
        assert isinstance(arg, int)

    t = TranslationContext()
    t.config.translation.gc = 'boehm'
    src = py.code.Source("""
    def entry_point(argv):
        args = (%s,)
        res = function(*args)
        print res
        return 0
    """ % (", ".join(['int(argv[%d])' % (i + 1) for i in range(len(args))]),))
    exec src.compile() in locals()

    t.buildannotator().build_types(function, [int] * len(args))
    t.buildrtyper().specialize()
    warmrunnerdesc = WarmRunnerDesc(t, translate_support_code=True,
                                    CPUClass=CPU386,
                                    **kwds)
    warmrunnerdesc.state.set_param_threshold(3)          # for tests
    warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
    mixlevelann = warmrunnerdesc.annhelper
    entry_point_graph = mixlevelann.getgraph(entry_point, [s_list_of_strings],
                                             annmodel.SomeInteger())
    warmrunnerdesc.finish()
    # XXX patch exceptions
    cbuilder = CBuilder(t, entry_point, config=t.config)
    cbuilder.generate_source()
    exe_name = cbuilder.compile()
    log('---------- Test starting ----------')
    stdout = cbuilder.cmdexec(" ".join([str(arg) for arg in args]))
    res = int(stdout)
    log('---------- Test done (%d) ----------' % (res,))
    return res
