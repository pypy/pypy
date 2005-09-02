import py

from pypy.tool.udir import udir 
from pypy.translator.tool.cbuild import build_executable 

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
    
