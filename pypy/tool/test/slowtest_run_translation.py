import os
from pypy.tool.run_translation import *

repository = "http://codespeak.net/svn/pypy/dist"
tmpdir = os.tmpnam()
testfile = os.path.join(tmpdir, "pypy", "translator", "gencl.py")
testrev = 14373

class  TestRunTranslation:
    def test_prepare_cleanup(self):
        execdata = prepare(repository, tmpdir, testrev)
        assert os.path.exists(testfile)
        cleanup(execdata)
        assert not os.path.exists(tmpdir)

    def test_execute(self):
        execdata = prepare(repository, tmpdir, testrev)
        execute("targetpypymain", execdata)

