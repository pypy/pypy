# XXX copy and paste from backend/x86/support.py
import py
from pypy.jit.metainterp.history import log


def c_meta_interp(function, args, repeat=1, optimizer='ignored', **kwds):
    from pypy.translator.translator import TranslationContext
    from pypy.jit.metainterp.warmspot import WarmRunnerDesc
    from pypy.jit.metainterp.simple_optimize import Optimizer
    from pypy.jit.backend.minimal.runner import LLtypeCPU
    from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
    from pypy.annotation.listdef import s_list_of_strings
    from pypy.annotation import model as annmodel
    
    for arg in args:
        assert isinstance(arg, int)

    t = TranslationContext()
    t.config.translation.gc = 'boehm'
    if repeat != 1:
        src = py.code.Source("""
        def entry_point(argv):
            args = (%s,)
            res = function(*args)
            for k in range(%d - 1):
                res = function(*args)
            print res
            return 0
        """ % (", ".join(['int(argv[%d])' % (i + 1) for i in range(len(args))]), repeat))
    else:
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
                                    CPUClass=LLtypeCPU,
                                    optimizer=Optimizer,
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
