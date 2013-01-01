
""" File containing maemo platform tests
"""

import py
from rpython.tool.udir import udir
from rpython.translator.platform.maemo import Maemo, check_scratchbox
from rpython.translator.platform.test.test_platform import TestPlatform as BasicTest
from rpython.translator.tool.cbuild import ExternalCompilationInfo

class TestMaemo(BasicTest):
    platform = Maemo()
    strict_on_stderr = False

    def setup_class(cls):
        py.test.skip("TestMaemo: tests skipped for now")
        check_scratchbox()

    def test_includes_outside_scratchbox(self):
        cfile = udir.join('test_includes_outside_scratchbox.c')
        cfile.write('''
        #include <stdio.h>
        #include "test.h"
        int main()
        {
            printf("%d\\n", XXX_STUFF);
            return 0;
        }
        ''')
        includedir = py.path.local(__file__).dirpath().join('include')
        eci = ExternalCompilationInfo(include_dirs=(includedir,))
        executable = self.platform.compile([cfile], eci)
        res = self.platform.execute(executable)
        self.check_res(res)

    def test_environment_inheritance(self):
        py.test.skip("FIXME")
