
from pypy.translator.platform import host, CompilationError
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from StringIO import StringIO
import sys

def test_echo():
    res = host.execute('echo', '42 24')
    assert res.out == '42 24\n'

    if sys.platform == 'win32':
        # echo is a shell builtin on Windows
        res = host.execute('cmd', ['/c', 'echo', '42', '24'])
        assert res.out == '42 24\n'
    else:
        res = host.execute('echo', ['42', '24'])
        assert res.out == '42 24\n'

class TestMakefile(object):
    platform = host
    strict_on_stderr = True
    
    def test_simple_makefile(self):
        tmpdir = udir.join('simple_makefile' + self.__class__.__name__).ensure(dir=1)
        cfile = tmpdir.join('test_simple_enough.c')
        cfile.write('''
        #include <stdio.h>
        int main()
        {
            printf("42\\n");
            return 0;
        }
        ''')
        mk = self.platform.gen_makefile([cfile], ExternalCompilationInfo(),
                               path=tmpdir)
        mk.write()
        self.platform.execute_makefile(mk)
        res = self.platform.execute(tmpdir.join('test_simple_enough'))
        assert res.out == '42\n'
        if self.strict_on_stderr:
            assert res.err == ''
        assert res.returncode == 0

    def test_link_files(self):
        tmpdir = udir.join('link_files' + self.__class__.__name__).ensure(dir=1)
        eci = ExternalCompilationInfo(link_files=['/foo/bar.a'])
        mk = self.platform.gen_makefile(['blip.c'], eci, path=tmpdir)
        mk.write()
        assert 'LINKFILES = /foo/bar.a' in tmpdir.join('Makefile').read()

class TestMaemo(TestMakefile):
    strict_on_stderr = False
    
    def setup_class(cls):
        from pypy.translator.platform.maemo import check_scratchbox, Maemo
        check_scratchbox()
        cls.platform = Maemo()
