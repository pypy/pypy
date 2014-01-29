
import py, sys, ctypes, os
from rpython.tool.udir import udir
from rpython.translator.platform import CompilationError, Platform
from rpython.translator.platform import host
from rpython.translator.tool.cbuild import ExternalCompilationInfo

def test_compilationerror_repr():
    # compilation error output/stdout may be large, but we don't want
    # repr to create a limited version
    c = CompilationError('', '*'*1000)
    assert repr(c) == 'CompilationError(err="""\n\t%s""")' % ('*'*1000,)
    c = CompilationError('*'*1000, '')
    assert repr(c) == 'CompilationError(out="""\n\t%s""")' % ('*'*1000,)

class TestPlatform(object):
    platform = host
    strict_on_stderr = True
    
    def check_res(self, res, expected='42\n'):
        assert res.out == expected
        if self.strict_on_stderr:
            assert res.err == ''
        assert res.returncode == 0        
    
    def test_simple_enough(self):
        cfile = udir.join('test_simple_enough.c')
        cfile.write('''
        #include <stdio.h>
        int main()
        {
            printf("42\\n");
            return 0;
        }
        ''')
        executable = self.platform.compile([cfile], ExternalCompilationInfo())
        res = self.platform.execute(executable)
        self.check_res(res)

    def test_two_files(self):
        cfile = udir.join('test_two_files.c')
        cfile.write('''
        #include <stdio.h>
        int func();
        int main()
        {
            printf("%d\\n", func());
            return 0;
        }
        ''')
        cfile2 = udir.join('implement1.c')
        cfile2.write('''
        int func()
        {
            return 42;
        }
        ''')
        executable = self.platform.compile([cfile, cfile2], ExternalCompilationInfo())
        res = self.platform.execute(executable)
        self.check_res(res)

    def test_900_files(self):
        txt = '#include <stdio.h>\n'
        for i in range(900):
            txt += 'int func%03d();\n' % i
        txt += 'int main() {\n    int j=0;'    
        for i in range(900):
            txt += '    j += func%03d();\n' % i
        txt += '    printf("%d\\n", j);\n'
        txt += '    return 0;};\n'
        cfile = udir.join('test_900_files.c')
        cfile.write(txt)
        cfiles = [cfile]
        for i in range(900):
            cfile2 = udir.join('implement%03d.c' %i)
            cfile2.write('''
                int func%03d()
            {
                return %d;
            }
            ''' % (i, i))
            cfiles.append(cfile2)
        mk = self.platform.gen_makefile(cfiles, ExternalCompilationInfo(), path=udir)
        mk.write()
        self.platform.execute_makefile(mk)
        res = self.platform.execute(udir.join('test_900_files'))
        self.check_res(res, '%d\n' %sum(range(900)))

    def test_precompiled_headers(self):
        import time
        tmpdir = udir.join('precompiled_headers').ensure(dir=1)
        # Create an eci that should not use precompiled headers
        eci = ExternalCompilationInfo(include_dirs=[tmpdir])
        main_c = tmpdir.join('main_no_pch.c')
        eci.separate_module_files = [main_c]
        ncfiles = 10
        nprecompiled_headers = 20
        txt = ''
        for i in range(ncfiles):
            txt += "int func%03d();\n" % i
        txt += "\nint main(int argc, char * argv[])\n"
        txt += "{\n   int i=0;\n"
        for i in range(ncfiles):
            txt += "   i += func%03d();\n" % i
        txt += '    printf("%d\\n", i);\n'
        txt += "   return 0;\n};\n"
        main_c.write(txt)
        # Create some large headers with dummy functions to be precompiled
        cfiles_precompiled_headers = []
        for i in range(nprecompiled_headers):
            pch_name =tmpdir.join('pcheader%03d.h' % i)
            txt = ''
            for j in range(3000):
                txt += "int pcfunc%03d_%03d();\n" %(i, j)
            pch_name.write(txt)    
            cfiles_precompiled_headers.append(pch_name)        
        # Create some cfiles with headers we want precompiled
        cfiles = []
        for i in range(ncfiles):
            c_name =tmpdir.join('implement%03d.c' % i)
            txt = ''
            for pch_name in cfiles_precompiled_headers:
                txt += '#include "%s"\n' % pch_name
            txt += "int func%03d(){ return %d;};\n" % (i, i)
            c_name.write(txt)
            cfiles.append(c_name)        
        mk = self.platform.gen_makefile(cfiles, eci, path=udir,
                           cfile_precompilation=cfiles_precompiled_headers)
        if sys.platform == 'win32':
            clean = ('clean', '', 'for %f in ( $(OBJECTS) $(TARGET) ) do @if exist %f del /f %f')
        else:    
            clean = ('clean', '', 'rm -f $(OBJECTS) $(TARGET) ')
        mk.rule(*clean)
        mk.write()
        t0 = time.clock()
        self.platform.execute_makefile(mk)
        t1 = time.clock()
        t_precompiled = t1 - t0
        res = self.platform.execute(mk.exe_name)
        self.check_res(res, '%d\n' %sum(range(ncfiles)))
        self.platform.execute_makefile(mk, extra_opts=['clean'])
        #Rewrite a non-precompiled header makefile
        mk = self.platform.gen_makefile(cfiles, eci, path=udir)
        mk.rule(*clean)
        mk.write()
        t0 = time.clock()
        self.platform.execute_makefile(mk)
        t1 = time.clock()
        t_normal = t1 - t0
        print "precompiled haeder 'make' time %.2f, non-precompiled header time %.2f" %(t_precompiled, t_normal)
        assert t_precompiled < t_normal * 0.5

    def test_nice_errors(self):
        cfile = udir.join('test_nice_errors.c')
        cfile.write('')
        try:
            executable = self.platform.compile([cfile], ExternalCompilationInfo())
        except CompilationError, e:
            filename = cfile.dirpath().join(cfile.purebasename + '.errors')
            assert filename.read('r') == e.err
        else:
            py.test.fail("Did not raise")

    def test_use_eci(self):
        tmpdir = udir.join('use_eci').ensure(dir=1)
        hfile = tmpdir.join('needed.h')
        hfile.write('#define SOMEHASHDEFINE 42\n')
        eci = ExternalCompilationInfo(include_dirs=[tmpdir])
        cfile = udir.join('use_eci_c.c')
        cfile.write('''
        #include <stdio.h>
        #include "needed.h"
        int main()
        {
            printf("%d\\n", SOMEHASHDEFINE);
            return 0;
        }
        ''')
        executable = self.platform.compile([cfile], eci)
        res = self.platform.execute(executable)
        self.check_res(res)

    def test_standalone_library(self):
        tmpdir = udir.join('standalone_library').ensure(dir=1)
        c_file = tmpdir.join('stand1.c')
        c_file.write('''
        #include <math.h>
        #include <stdio.h>

        int main()
        {
            printf("%f\\n", pow(2.0, 2.0));
        }''')
        if sys.platform != 'win32':
            eci = ExternalCompilationInfo(
                libraries = ['m'],
                )
        else:
            eci = ExternalCompilationInfo()
        executable = self.platform.compile([c_file], eci)
        res = self.platform.execute(executable)
        assert res.out.startswith('4.0')

    def test_environment_inheritance(self):
        # make sure that environment is inherited
        cmd = 'import os; print os.environ["_SOME_VARIABLE_%d"]'
        res = self.platform.execute(sys.executable, ['-c', cmd % 1],
                                    env={'_SOME_VARIABLE_1':'xyz'})
        assert 'xyz' in res.out
        os.environ['_SOME_VARIABLE_2'] = 'zyz'
        try:
            res = self.platform.execute('python', ['-c', cmd % 2])
            assert 'zyz' in res.out
        finally:
            del os.environ['_SOME_VARIABLE_2']

    def test_key(self):
        class XPlatform(Platform):
            relevant_environ = ['CPATH']
            
            def __init__(self):
                self.cc = 'xcc'
        x = XPlatform()
        res = x.key()
        assert res.startswith("XPlatform cc='xcc' CPATH=")

def test_equality():
    class X(Platform):
        def __init__(self):
            pass
    class Y(Platform):
        def __init__(self, x):
            self.x = x

    assert X() == X()
    assert Y(3) == Y(3)
    assert Y(2) != Y(3)


def test_is_host_build():
    from rpython.translator import platform
    assert platform.host == platform.platform

    assert platform.is_host_build()
    platform.set_platform('maemo', None)
    assert platform.host != platform.platform
    assert not platform.is_host_build()
