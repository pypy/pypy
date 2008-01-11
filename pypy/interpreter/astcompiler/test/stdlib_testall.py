import pypy 
import py
from pypy.interpreter.astcompiler.test.test_compiler import \
        compile_with_astcompiler

class TestStdlib:

    def check_file_compile(self, filepath):
        space = self.space
        print 'Compiling:', filepath 
        source = filepath.read() 
        compile_with_astcompiler(source, mode='exec', space=space)

    def test_all(self):
        p = py.path.local(pypy.__file__).dirpath().dirpath('lib-python',
                                                           '2.4.1')
        files = p.listdir("*.py")
        files.sort()
        for s in files:
            yield self.check_file_compile, s
