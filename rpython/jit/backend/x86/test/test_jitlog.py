import re
from rpython.rlib import debug
from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp import logger
from rpython.jit.metainterp.typesystem import llhelper
from StringIO import StringIO
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.history import AbstractDescr, JitCellToken, BasicFailDescr, BasicFinalDescr
from rpython.jit.backend.model import AbstractCPU
from rpython.rlib.jit import JitDriver
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.rlib.rvmprof import rvmprof
import tempfile

class TestLogger(Jit386Mixin):

    def test_log_loop(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'res'])
        vmprof = rvmprof.VMProf()
        fileno, name = tempfile.mkstemp()
        def f(x, y):
            res = 0
            vmprof.enable(fileno, 0.1)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, res=res)
                myjitdriver.jit_merge_point(x=x, y=y, res=res)
                res += x
                if res > 40:
                    res += 1
                    res -= 2
                    res += 1
                y -= 1
            return res
        res = self.meta_interp(f, [6, 20])
        self.check_trace_count(2)
        print(name)
