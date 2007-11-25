import py, sys

from pypy.tool.udir import udir 
from pypy.translator.tool.cbuild import build_executable, \
     ExternalCompilationInfo, compile_c_module
from subprocess import Popen, PIPE, STDOUT

def test_simple_executable(): 
    print udir
    testpath = udir.join('testbuildexec')
    t = testpath.ensure("test.c")
    t.write(r"""
        #include <stdio.h>
        int main() {
            printf("hello world\n");
            return 0;
        }
""")
    eci = ExternalCompilationInfo()
    testexec = build_executable([t], eci)
    out = py.process.cmdexec(testexec)
    assert out.startswith('hello world')
    
def test_compile_threads():
    if sys.platform == 'nt':
        py.test.skip("Linux-specific test")
    try:
        import ctypes
    except ImportError:
        py.test.skip("Need ctypes for that test")
    from pypy.tool.autopath import pypydir
    pypydir = py.path.local(pypydir)
    csourcedir = pypydir.join('translator', 'c', 'src')
    include_dirs = [str(csourcedir.dirpath())]
    files = [csourcedir.join('thread.c')]
    eci = ExternalCompilationInfo(
        include_dirs=include_dirs,
        libraries=['pthread']
    )
    mod = compile_c_module(files, '_thread', eci)
    cdll = ctypes.CDLL(mod)
    assert hasattr(cdll, 'RPyThreadLockInit')

class TestEci:
    def setup_class(cls):
        tmpdir = udir.ensure('testeci', dir=1)
        c_file = tmpdir.join('module.c')
        c_file.write(py.code.Source('''
        int sum(int x, int y)
        {
            return x + y;
        }
        '''))
        cls.modfile = c_file
        cls.tmpdir = tmpdir

    def test_standalone(self):
        tmpdir = self.tmpdir
        c_file = tmpdir.join('stand1.c')
        c_file.write('''
        #include <math.h>
        #include <stdio.h>
        
        int main()
        {
            printf("%f\\n", pow(2.0, 2.0));
        }''')
        eci = ExternalCompilationInfo(
            libraries = ['m'],
        )
        output = build_executable([c_file], eci)
        p = Popen(output, stdout=PIPE, stderr=STDOUT)
        p.wait()
        assert p.stdout.readline().startswith('4.0')
    
    def test_merge(self):
        e1 = ExternalCompilationInfo(
            pre_include_lines  = ['1'],
            includes           = ['x.h'],
            post_include_lines = ['p1']
        )
        e2 = ExternalCompilationInfo(
            pre_include_lines  = ['2'],
            includes           = ['x.h', 'y.h'],
            post_include_lines = ['p2'],
        )
        e3 = ExternalCompilationInfo(
            pre_include_lines  = ['3'],
            includes           = ['y.h', 'z.h'],
            post_include_lines = ['p3']
        )
        e = e1.merge(e2, e3)
        assert e.pre_include_lines == ('1', '2', '3')
        assert e.includes == ('x.h', 'y.h', 'z.h')
        assert e.post_include_lines == ('p1', 'p2', 'p3')

    def test_convert_sources_to_c_files(self):
        eci = ExternalCompilationInfo(
            separate_module_sources = ['xxx'],
            separate_module_files = ['x.c'],
        )
        cache_dir = udir.join('test_convert_sources').ensure(dir=1)
        neweci = eci.convert_sources_to_files(cache_dir)
        assert not neweci.separate_module_sources
        res = neweci.separate_module_files
        assert len(res) == 2
        assert res[0] == 'x.c'
        assert str(res[1]).startswith(str(cache_dir))
        e = ExternalCompilationInfo()
        assert e.convert_sources_to_files() is e

    def test_make_shared_lib(self):
        eci = ExternalCompilationInfo(
            separate_module_sources = ['''
            int get()
            {
                return 42;
            }''']
        )
        neweci = eci.compile_shared_lib()
        assert len(neweci.libraries) == 1
        try:
            import ctypes
        except ImportError:
            py.test.skip("Need ctypes for that test")
        assert ctypes.CDLL(neweci.libraries[0]).get() == 42
        assert not neweci.separate_module_sources
        assert not neweci.separate_module_files
