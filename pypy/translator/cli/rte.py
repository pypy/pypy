"""
Support for an automatically compiled Run Time Environment.
The source of the RTE is in the src/ directory.
"""
import os
import os.path
import shutil

import py
from py.compat import subprocess
from pypy.translator.cli.sdk import SDK
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("cli")
py.log.setconsumer("cli", ansi_log)


class Target:
    SOURCES = []
    OUTPUT = None
    ALIAS = None
    FLAGS = []
    DEPENDENCIES = []
    SRC_DIR = os.path.join(os.path.dirname(__file__), 'src/')

    def _filename(cls, name, path=None):
        rel_path =  os.path.join(cls.SRC_DIR, name)
        return os.path.abspath(rel_path)
    _filename = classmethod(_filename)

    def get_COMPILER(cls):
        return SDK.csc()
    get_COMPILER = classmethod(get_COMPILER)
    
    def get(cls):
        for dep in cls.DEPENDENCIES:
            dep.get()
        sources = [cls._filename(src) for src in cls.SOURCES]
        out = cls._filename(cls.OUTPUT)
        alias = cls._filename(cls.ALIAS or cls.OUTPUT)
        recompile = True
        try:
            src_mtime = max([os.stat(src).st_mtime for src in sources])
            alias_mtime = os.stat(alias).st_mtime
            if src_mtime <= alias_mtime:
                recompile = False
        except OSError:
            pass

        if recompile:
            cls.compile(sources, out)
        return out
    get = classmethod(get)

    def compile(cls, sources, out):
        log.red("Compiling %s" % (cls.ALIAS or cls.OUTPUT))
        oldcwd = os.getcwd()
        os.chdir(cls.SRC_DIR)
        compiler = subprocess.Popen([cls.get_COMPILER()] + cls.FLAGS + ['/out:%s' % out] + sources,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        retval = compiler.wait()
        assert retval == 0, 'Failed to compile %s: the compiler said:\n %s' % (
            cls.OUTPUT, stdout + stderr)
        if cls.ALIAS is not None:
            alias = cls._filename(cls.ALIAS)
            shutil.copy(out, alias)
        os.chdir(oldcwd)

    compile = classmethod(compile)

class MainStub(Target):
    SOURCES = ['stub/main.il']
    OUTPUT = 'main.exe'

    def get_COMPILER(cls):
        return SDK.ilasm()
    get_COMPILER = classmethod(get_COMPILER)
    
class PyPyLibDLL(Target):
    SOURCES = ['pypylib.cs', 'll_os.cs', 'll_os_path.cs', 'errno.cs', 'll_math.cs',
               'debug.cs']
    OUTPUT = 'pypylib.dll'
    FLAGS = ['/t:library', '/unsafe', '/r:main.exe']
    DEPENDENCIES = [MainStub]

    def compile(cls, sources, out):
        from pypy.translator.cli.query import pypylib
        remove_cache_for_assembly(pypylib)
        Target.compile.im_func(cls, sources, out)
    compile = classmethod(compile)


class RPythonNetModule(Target):
    SOURCES = []
    OUTPUT = 'rpython.netmodule'

    def compile(cls, sources, out):
        pass

class Query(Target):
    SOURCES = ['query.cs']
    OUTPUT = 'query.exe'

    def compile(cls, sources, out):
        # assume that if query.exe need to be recompiled the descriptions cache is invalid        
        from pypy.translator.cli.query import mscorlib, pypylib
        remove_cache_for_assembly(mscorlib)
        remove_cache_for_assembly(pypylib)
        Target.compile.im_func(cls, sources, out)
    compile = classmethod(compile)

class Support(Target):
    SOURCES = ['support.cs']
    OUTPUT = 'support.dll'
    FLAGS = ['/t:library']

def get_pypy_dll():
    return PyPyLibDLL.get()

def remove_cache_for_assembly(ass):
    from pypy.translator.cli.query import get_cachedir
    cache = get_cachedir().join(ass + '.pickle')
    if cache.check():
        cache.remove()

if __name__ == '__main__':
    import shutil
    pypylib = get_pypy_dll()
    shutil.copy(pypylib, '.')
