import os
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import s_list_of_strings
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.jit.timeshifter.test import test_timeshift
from pypy.translator.c.genc import CStandaloneBuilder

import py; py.test.skip("in-progress")


class TestTimeshiftI386(test_timeshift.TestTimeshift):
    from pypy.jit.codegen.i386.ri386genop import RI386GenOp as RGenOp

    def timeshift_test(self, ll_runner, residual_args):
        RGenOp = self.RGenOp
        FUNC = self.FUNCTYPE
        SEPLINE = 'running residual graph...\n'

        def ll_main(argv):
            rgenop = RGenOp.get_rgenop_for_testing()
            gv_generated = ll_runner(rgenop)
            generated = gv_generated.revealconst(lltype.Ptr(FUNC))
            os.write(1, SEPLINE)
            res = generated(*residual_args)
            os.write(1, str(res) + '\n')
            keepalive_until_here(rgenop)    # to keep the code blocks alive
            return 0

        annhelper = self.htshift.annhelper
        annhelper.getgraph(ll_main, [s_list_of_strings],
                           annmodel.SomeInteger())
        annhelper.finish()

        t = self.rtyper.annotator.translator
        cbuilder = CStandaloneBuilder(t, ll_main)
        cbuilder.generate_source()
        cbuilder.compile()
        output = cbuilder.cmdexec()
        assert output.startswith(SEPLINE)
        lastline = output[len(SEPLINE):].strip()
        return int(lastline)

    def check_insns(self, expected=None, **counts):
        "Cannot check instructions in the generated assembler."

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py
