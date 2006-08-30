import os
from pypy.rpython.objectmodel import specialize
from pypy.annotation import model as annmodel
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.i386.ri386genop import RI386GenOp, IntConst


class Whatever(object):
    def __eq__(self, other):
        return True

class I386LLInterpTimeshiftingTestMixin(object):
    class RGenOp(RI386GenOp):
        from pypy.jit.codegen.i386.codebuf import LLTypeMachineCodeBlock as MachineCodeBlock

        @staticmethod
        @specialize.memo()
        def fieldToken(T, name):
            return list(T._names).index(name)

        @staticmethod
        @specialize.memo()
        def arrayToken(A):
            return 0, 1, 1

        @staticmethod
        @specialize.memo()
        def allocToken(T):
            return len(T._names)

        @staticmethod
        @specialize.memo()
        def constFieldName(T, name):
            return IntConst(list(T._names).index(name))

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


class TestTimeshiftI386LLInterp(I386LLInterpTimeshiftingTestMixin,
                                test_timeshift.TestTimeshift):
    
    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    pass

