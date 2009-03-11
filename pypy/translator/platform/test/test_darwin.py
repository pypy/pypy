
""" File containing darwin platform tests
"""

import py, os
if os.name != 'darwin':
    py.test.skip("Darwin only")

from pypy.tool.udir import udir
from pypy.translator.platform.darwin import Darwin
from pypy.translator.platform.test.test_platform import TestPlatform as BasicTest
from pypy.translator.tool.cbuild import ExternalCompilationInfo

class TestDarwin(BasicTest):
    platform = Darwin()

    def test_frameworks(self):
        objcfile = udir.join('test_simple.m')
        objcfile.write(r'''
        #import <Foundation/Foundation.h>
        #include "test.h"

        int main (int argc, const char * argv[]) {
            NSAutoreleasePool *pool = [[NSAutoreleasePool alloc] init];
            NSArray *args = [[NSProcessInfo processInfo] arguments];
            NSCountedSet *cset = [[NSCountedSet alloc] initWithArray:args];

            printf("%d\n", XXX_STUFF);

            [cset release];
            [pool release];
            return 0;
        }
        ''')
        includedir = py.magic.autopath().dirpath().join('include')
        eci = ExternalCompilationInfo(frameworks=('Cocoa',),
                                      include_dirs=(includedir,))
        executable = self.platform.compile([objcfile], eci)
        res = self.platform.execute(executable)
        self.check_res(res)

