from rpython.jit.metainterp.optimizeopt.test.test_optimizeopt import OptimizeOptTest
from rpython.jit.metainterp.optimizeopt.test.test_util import LLtypeMixin
from rpython.jit.metainterp.resoperation import rop


allopts = OptimizeOptTest.enable_opts.split(':')
for optnum in range(len(allopts)):
    myopts = allopts[:]
    del myopts[optnum]

    class TestLLtype(OptimizeOptTest, LLtypeMixin):
        enable_opts = ':'.join(myopts)

        def optimize_loop(self, ops, expected, expected_preamble=None,
                          call_pure_results=None, expected_short=None):
            loop = self.parse(ops, postprocess=self.postprocess)
            if expected != "crash!":
                expected = self.parse(expected)
            if expected_preamble:
                expected_preamble = self.parse(expected_preamble)
            if expected_short:
                expected_short = self.parse(expected_short)

            preamble = self.unroll_and_optimize(loop, call_pure_results)

            for op in preamble.operations + loop.operations:
                assert op.getopnum() not in (rop.CALL_PURE,
                                             rop.CALL_LOOPINVARIANT,
                                             rop.VIRTUAL_REF_FINISH,
                                             rop.VIRTUAL_REF,
                                             rop.QUASIIMMUT_FIELD,
                                             rop.MARK_OPAQUE_PTR,
                                             rop.RECORD_KNOWN_CLASS)

        def raises(self, e, fn, *args):
            try:
                fn(*args)
            except Exception, e:
                return e

    opt = allopts[optnum]
    exec "TestNo%sLLtype = TestLLtype" % (opt[0].upper() + opt[1:])

del TestLLtype # No need to run the last set twice
del TestNoUnrollLLtype # This case is take care of by test_optimizebasic
        
