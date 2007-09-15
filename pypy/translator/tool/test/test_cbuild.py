import py, sys

from pypy.tool.udir import udir 
from pypy.translator.tool.cbuild import build_executable, cache_c_module

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
    testexec = build_executable([t])
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
    cache_c_module(files, '_thread', cache_dir=udir, include_dirs=include_dirs,
                   libraries=['pthread'])
    cdll = ctypes.CDLL(str(udir.join('_thread.so')))
    assert hasattr(cdll, 'RPyThreadLockInit')

