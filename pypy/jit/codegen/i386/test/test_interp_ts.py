import os
from pypy.annotation import model as annmodel
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.i386.ri386genop import RI386GenOp

import py; py.test.skip("in-progress")


class TestTimeshiftI386LLInterp(test_timeshift.TestTimeshift):
    class RGenOp(RI386GenOp):
        from pypy.jit.codegen.i386.codebuf import LLTypeMachineCodeBlock as MachineCodeBlock
    
    def timeshift(self, ll_function, values, opt_consts=[], *args, **kwds):
        self.timeshift_cached(ll_function, values, *args, **kwds)

        mainargs = []
        residualargs = []
        for i, (color, llvalue) in enumerate(zip(self.argcolors, values)):
            if color == "green":
                mainargs.append(llvalue)
            else:
                mainargs.append(i in opt_consts)
                mainargs.append(llvalue)
                residualargs.append(llvalue)

        # run the graph generator
        from pypy.rpython.llinterp import LLInterpreter
        llinterp = LLInterpreter(self.rtyper)
        ll_generated = llinterp.eval_graph(self.maingraph, mainargs)

        # XXX test more


    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py
