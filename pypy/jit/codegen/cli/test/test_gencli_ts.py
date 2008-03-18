import py
from pypy.tool.udir import udir
from pypy.translator.cli.entrypoint import StandaloneEntryPoint
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.sdk import SDK
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.cli.rgenop import RCliGenOp

class CliTimeshiftingTestMixin(I386TimeshiftingTestMixin):
    RGenOp = RCliGenOp

    def getgraph(self, fn):
        bk = self.rtyper.annotator.bookkeeper
        return bk.getdesc(fn).getuniquegraph()

    def compile(self, ll_main):
        graph = self.getgraph(ll_main)
        entrypoint = StandaloneEntryPoint(graph)
        gen = GenCli(udir, self.rtyper.annotator.translator, entrypoint)
        gen.generate_source()
        self.executable_name = gen.build_exe()

    def cmdexec(self, args=''):
        assert self.executable_name
        mono = ''.join(SDK.runtime())
        return py.process.cmdexec('%s "%s" %s' % (mono, self.executable_name, args))


class TestTimeshiftCli(CliTimeshiftingTestMixin,
                       test_timeshift.TestOOType):

    passing_ootype_tests = set([
        'test_very_simple',
        'test_convert_const_to_redbox',
        'test_simple_opt_const_propagation1',
        'test_simple_opt_const_propagation2',
        'test_loop_folding',
#        'test_loop_merging',
#        'test_two_loops_merging',
        'test_convert_greenvar_to_redvar',
#        'test_green_across_split',
#        'test_merge_const_before_return',
#        'test_merge_3_redconsts_before_return',
        'test_merge_const_at_return',
#        'test_arith_plus_minus',
        ])

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass
