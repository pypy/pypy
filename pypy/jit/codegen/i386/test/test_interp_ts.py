import os
from pypy.annotation import model as annmodel
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.i386.ri386genop import RI386GenOp, IntConst

import py; py.test.skip("in-progress")


class Whatever(object):
    def __eq__(self, other):
        return True


class TestTimeshiftI386LLInterp(test_timeshift.TestTimeshift):
    class RGenOp(RI386GenOp):
        from pypy.jit.codegen.i386.codebuf import LLTypeMachineCodeBlock as MachineCodeBlock

        def constFieldName(T, name):
            return IntConst(list(T._names).index(name))
        constFieldName._annspecialcase_ = 'specialize:memo'
        constFieldName = staticmethod(constFieldName)

        def access_array(A):
            return 0, 1, 1
        access_array._annspecialcase_ = 'specialize:memo'
        access_array = staticmethod(access_array)

    def timeshift(self, ll_function, values, opt_consts=[], *args, **kwds):
        values = self.timeshift_cached(ll_function, values, *args, **kwds)

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

        return Whatever()

    def check_insns(self, expected=None, **counts):
        pass


    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py
