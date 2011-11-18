
""" File containing darwin platform tests
"""

import py, sys, platform
if sys.platform != 'darwin':
    py.test.skip("Darwin only")

from pypy.tool.udir import udir
from pypy.translator.platform.darwin import Darwin_i386, Darwin_x86_64, Darwin_PowerPC
from pypy.translator.platform.test.test_platform import TestPlatform as BasicTest
from pypy.translator.tool.cbuild import ExternalCompilationInfo

if platform.machine() == 'i386':
    if sys.maxint <= 2147483647:
        host_factory = Darwin_i386
    else:
        host_factory = Darwin_x86_64
else:
    host_factory = Darwin_PowerPC

class TestDarwin(BasicTest):
    platform = host_factory()

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
        includedir = py.path.local(__file__).dirpath().join('include')
        eci = ExternalCompilationInfo(frameworks=('Cocoa',),
                                      include_dirs=(includedir,))
        executable = self.platform.compile([objcfile], eci)
        res = self.platform.execute(executable)
        self.check_res(res)

    def test_64_32_results(self):
        if platform.machine() != 'i386':
            py.test.skip("i386 only")
        plat32 = Darwin_i386()
        plat64 = Darwin_x86_64()
        cfile = udir.join('test_int_size.c')
        cfile.write(r'''
        #include <stdio.h>
        #include <limits.h>

        int main() {
                printf("%d\n", INT_MAX < LONG_MAX);
                return 0;
        }
        ''')
        eci = ExternalCompilationInfo()
        executable = plat32.compile([cfile], eci)
        res = plat32.execute(executable)
        self.check_res(res, '0\n')
        if host_factory == Darwin_x86_64:
            executable = plat64.compile([cfile], eci)
            res = plat64.execute(executable)
            self.check_res(res, '1\n')

    def test_longsize(self):
        if platform.machine() != 'i386':
            py.test.skip("i386 only")
        cfile = udir.join('test_int_size.c')
        cfile.write(r'''
        #include <stdio.h>
        #include <limits.h>

        int main() {
                printf("%ld\n", LONG_MAX);
                return 0;
        }
        ''')
        eci = ExternalCompilationInfo()
        executable = self.platform.compile([cfile], eci)
        res = self.platform.execute(executable)
        self.check_res(res, str(sys.maxint) + '\n')
        
    def test_32bit_makefile(self):
        if platform.machine() != 'i386':
            py.test.skip("i386 only")
        plat32 = Darwin_i386()
        plat64 = Darwin_x86_64()
        eci = ExternalCompilationInfo()
        cfile_content =r'''
        #include <stdio.h>
        #include <limits.h>

        int main() {
                printf("%d\n", INT_MAX < LONG_MAX);
                return 0;
        }
        '''

        tmpdir = udir.join('32_makefile' + self.__class__.__name__).ensure(dir=1)
        cfile = tmpdir.join('test_int_size.c')
        cfile.write(cfile_content)
        mk = plat32.gen_makefile([cfile], ExternalCompilationInfo(),
                               path=tmpdir)
        mk.write()
        plat32.execute_makefile(mk)
        res = plat32.execute(tmpdir.join('test_int_size'))
        self.check_res(res, '0\n')
        if host_factory == Darwin_x86_64:
            tmpdir = udir.join('64_makefile' + self.__class__.__name__).ensure(dir=1)
            cfile = tmpdir.join('test_int_size.c')
            cfile.write(cfile_content)
            mk = plat64.gen_makefile([cfile], ExternalCompilationInfo(),
                                   path=tmpdir)
            mk.write()
            plat64.execute_makefile(mk)
            res = plat64.execute(tmpdir.join('test_int_size'))
            self.check_res(res, '1\n')

