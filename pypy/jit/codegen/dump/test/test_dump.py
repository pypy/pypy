import os
from pypy.rpython.lltypesystem import lltype
from pypy.jit.codegen.dump.rgenop import RDumpGenOp, LOGFILE


# XXX very incomplete

FUNC0 = lltype.FuncType([], lltype.Signed)


class TestRDumpGenOp:

    def setup_method(self, meth):
        try:
            os.unlink(LOGFILE)
        except OSError:
            pass

    def getlog(self):
        f = open(LOGFILE, 'r')
        data = f.read()
        f.close()
        os.unlink(LOGFILE)
        return data

    def test_genconst(self):
        rgenop = RDumpGenOp()
        builder, gv_callable, inputargs_gv = rgenop.newgraph(
            RDumpGenOp.sigToken(FUNC0), "foobar")
        builder.start_writing()
        builder.genop_same_as(RDumpGenOp.kindToken(lltype.Signed),
                              rgenop.genconst(0))
        log = self.getlog()
        assert 'rgenop.genconst(0)' in log
        builder.genop_same_as(RDumpGenOp.kindToken(lltype.Bool),
                              rgenop.genconst(False))
        log = self.getlog()
        assert 'rgenop.genconst(False)' in log
