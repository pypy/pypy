import py
from pypy.jit.metainterp.history import log
from pypy.translator.translator import TranslationContext

class BaseCompiledMixin(object):

    type_system = None
    CPUClass = None
    basic = False

    def _get_TranslationContext(self):
        return TranslationContext()

    def _compile_and_run(self, t, entry_point, entry_point_graph, args):
        raise NotImplementedError

    # XXX backendopt is ignored
    def meta_interp(self, function, args, repeat=1, backendopt=None, **kwds): # XXX ignored
        from pypy.jit.metainterp.warmspot import WarmRunnerDesc
        from pypy.annotation.listdef import s_list_of_strings
        from pypy.annotation import model as annmodel

        for arg in args:
            assert isinstance(arg, int)

        t = self._get_TranslationContext()
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
        t.buildrtyper(type_system=self.type_system).specialize()
        warmrunnerdesc = WarmRunnerDesc(t, translate_support_code=True,
                                        CPUClass=self.CPUClass,
                                        **kwds)
        warmrunnerdesc.state.set_param_threshold(3)          # for tests
        warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
        mixlevelann = warmrunnerdesc.annhelper
        entry_point_graph = mixlevelann.getgraph(entry_point, [s_list_of_strings],
                                                 annmodel.SomeInteger())
        warmrunnerdesc.finish()
        return self._compile_and_run(t, entry_point, entry_point_graph, args)

    def check_loops(self, *args, **kwds):
        pass

    def check_loop_count(self, *args, **kwds):
        pass

    def check_tree_loop_count(self, *args, **kwds):
        pass

    def check_enter_count(self, *args, **kwds):
        pass

    def check_enter_count_at_most(self, *args, **kwds):
        pass

    def interp_operations(self, *args, **kwds):
        py.test.skip("interp_operations test skipped")


class CCompiledMixin(BaseCompiledMixin):
    type_system = 'lltype'

    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.gc = 'boehm'
        return t

    def _compile_and_run(self, t, entry_point, entry_point_graph, args):
        from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
        # XXX patch exceptions
        cbuilder = CBuilder(t, entry_point, config=t.config)
        cbuilder.generate_source()
        exe_name = cbuilder.compile()
        log('---------- Test starting ----------')
        stdout = cbuilder.cmdexec(" ".join([str(arg) for arg in args]))
        res = int(stdout)
        log('---------- Test done (%d) ----------' % (res,))
        return res

class CliCompiledMixin(BaseCompiledMixin):
    type_system = 'ootype'

    def _compile_and_run(self, t, entry_point, entry_point_graph, args):
        from pypy.translator.cli.test.runtest import compile_graph
        func = compile_graph(entry_point_graph, t, nowrap=True, standalone=True)
        return func(*args)
