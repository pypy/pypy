import py
import sys
from pypy.rlib.debug import debug_print
from pypy.rlib.jit import OPTIMIZER_FULL
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
    def meta_interp(self, function, args, repeat=1, inline=False, trace_limit=sys.maxint,
                    backendopt=None, listcomp=False, **kwds): # XXX ignored
        from pypy.jit.metainterp.warmspot import WarmRunnerDesc
        from pypy.annotation.listdef import s_list_of_strings
        from pypy.annotation import model as annmodel

        for arg in args:
            assert isinstance(arg, int)

        self.pre_translation_hook()
        t = self._get_TranslationContext()
        t.config.translation.type_system = self.type_system # force typesystem-specific options
        if listcomp:
            t.config.translation.list_comprehension_operations = True

        arglist = ", ".join(['int(argv[%d])' % (i + 1) for i in range(len(args))])
        if len(args) == 1:
            arglist += ','
        arglist = '(%s)' % arglist
        if repeat != 1:
            src = py.code.Source("""
            def entry_point(argv):
                args = %s
                res = function(*args)
                for k in range(%d - 1):
                    res = function(*args)
                print res
                return 0
            """ % (arglist, repeat))
        else:
            src = py.code.Source("""
            def entry_point(argv):
                args = %s
                res = function(*args)
                print res
                return 0
            """ % (arglist,))
        exec src.compile() in locals()

        t.buildannotator().build_types(function, [int] * len(args))
        t.buildrtyper(type_system=self.type_system).specialize()
        warmrunnerdesc = WarmRunnerDesc(t, translate_support_code=True,
                                        CPUClass=self.CPUClass,
                                        **kwds)
        warmrunnerdesc.state.set_param_threshold(3)          # for tests
        warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
        warmrunnerdesc.state.set_param_trace_limit(trace_limit)
        warmrunnerdesc.state.set_param_inlining(inline)
        warmrunnerdesc.state.set_param_optimizer(OPTIMIZER_FULL)
        mixlevelann = warmrunnerdesc.annhelper
        entry_point_graph = mixlevelann.getgraph(entry_point, [s_list_of_strings],
                                                 annmodel.SomeInteger())
        warmrunnerdesc.finish()
        self.post_translation_hook()
        return self._compile_and_run(t, entry_point, entry_point_graph, args)

    def pre_translation_hook(self):
        pass

    def post_translation_hook(self):
        pass

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

    def check_max_trace_length(self, *args, **kwds):
        pass

    def check_aborted_count(self, *args, **kwds):
        pass

    def check_aborted_count_at_least(self, *args, **kwds):
        pass

    def interp_operations(self, *args, **kwds):
        py.test.skip("interp_operations test skipped")


class CCompiledMixin(BaseCompiledMixin):
    type_system = 'lltype'
    slow = False

    def setup_class(cls):
        if cls.slow:
            from pypy.jit.conftest import option
            if not option.run_slow_tests:
                py.test.skip("use --slow to execute this long-running test")

    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.gc = 'boehm'
        t.config.translation.list_comprehension_operations = True
        return t

    def _compile_and_run(self, t, entry_point, entry_point_graph, args):
        from pypy.translator.c.genc import CStandaloneBuilder as CBuilder
        # XXX patch exceptions
        cbuilder = CBuilder(t, entry_point, config=t.config)
        cbuilder.generate_source()
        self._check_cbuilder(cbuilder)
        exe_name = cbuilder.compile()
        debug_print('---------- Test starting ----------')
        stdout = cbuilder.cmdexec(" ".join([str(arg) for arg in args]))
        res = int(stdout)
        debug_print('---------- Test done (%d) ----------' % (res,))
        return res

    def _check_cbuilder(self, cbuilder):
        pass

class CliCompiledMixin(BaseCompiledMixin):
    type_system = 'ootype'

    def pre_translation_hook(self):
        from pypy.translator.oosupport.support import patch_os
        self.olddefs = patch_os()

    def post_translation_hook(self):
        from pypy.translator.oosupport.support import unpatch_os
        unpatch_os(self.olddefs) # restore original values

    def _compile_and_run(self, t, entry_point, entry_point_graph, args):
        from pypy.translator.cli.test.runtest import compile_graph
        func = compile_graph(entry_point_graph, t, nowrap=True, standalone=True)
        return func(*args)

    def run_directly(self, fn, args):
        from pypy.translator.cli.test.runtest import compile_function, get_annotation
        ann = [get_annotation(x) for x in args]
        clifunc = compile_function(fn, ann)
        return clifunc(*args)
