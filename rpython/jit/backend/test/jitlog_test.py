import re
import os
from rpython.rlib import debug
from rpython.jit.tool.oparser import pure_parse
from rpython.jit.metainterp import logger
from rpython.jit.metainterp.typesystem import llhelper
from rpython.rlib.rjitlog import rjitlog as jl
from StringIO import StringIO
from rpython.jit.metainterp.optimizeopt.util import equaloplists
from rpython.jit.metainterp.history import AbstractDescr, JitCellToken, BasicFailDescr, BasicFinalDescr
from rpython.jit.backend.model import AbstractCPU
from rpython.rlib.jit import JitDriver
from rpython.rlib.objectmodel import always_inline
from rpython.jit.metainterp.test.support import LLJitMixin
from rpython.rlib.rjitlog import rjitlog
import tempfile

class LoggerTest(LLJitMixin):

    def test_explicit_enable(self, tmpdir):
        file = tmpdir.join('jitlog')
        fileno = os.open(file.strpath, os.O_WRONLY | os.O_CREAT)
        enable_jitlog = lambda: rjitlog.enable_jitlog(fileno)
        f = self.run_sample_loop(enable_jitlog)
        self.meta_interp(f, [10, 0])

        assert os.path.exists(file.strpath)
        with file.open('rb') as f:
            # check the file header
            assert f.read(3) == jl.MARK_JITLOG_HEADER + jl.JITLOG_VERSION_16BIT_LE
            assert len(f.read()) > 0

    def test_env(self, monkeypatch, tmpdir):
        file = tmpdir.join('jitlog')
        monkeypatch.setenv("JITLOG", file.strpath)
        f = self.run_sample_loop(None)
        self.meta_interp(f, [10,0])
        assert os.path.exists(file.strpath)
        with file.open('rb') as fd:
            # check the file header
            assert fd.read(3) == jl.MARK_JITLOG_HEADER + jl.JITLOG_VERSION_16BIT_LE
            assert len(fd.read()) > 0

    def test_version(self, monkeypatch, tmpdir):
        file = tmpdir.join('jitlog')
        monkeypatch.setattr(jl, 'JITLOG_VERSION_16BIT_LE', '\xff\xfe')
        monkeypatch.setenv("JITLOG", file.strpath)
        f = self.run_sample_loop(None)
        self.meta_interp(f, [10,0])
        assert os.path.exists(file.strpath)
        with file.open('rb') as fd:
            # check the file header
            assert fd.read(3) == jl.MARK_JITLOG_HEADER + '\xff\xfe'
            assert len(fd.read()) > 0

    def test_version(self, monkeypatch, tmpdir):
        file = tmpdir.join('jitlog')
        monkeypatch.setattr(jl, 'JITLOG_VERSION_16BIT_LE', '\xff\xfe')
        monkeypatch.setenv("JITLOG", file.strpath)
        f = self.run_sample_loop(None)
        self.meta_interp(f, [10,0])
        assert os.path.exists(file.strpath)
        with file.open('rb') as fd:
            # check the file header
            assert fd.read(3) == jl.MARK_JITLOG_HEADER + '\xff\xfe'
            assert len(fd.read()) > 0

    def run_sample_loop(self, func, myjitdriver = None):
        if not myjitdriver:
            myjitdriver = JitDriver(greens = [], reds = 'auto')
        def f(y, x):
            res = 0
            if func:
                func()
            while y > 0:
                myjitdriver.jit_merge_point()
                res += x
                y -= 1
            return res
        return f
