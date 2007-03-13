"""
Support for an automatically compiled Run Time Environment.
The source of the RTE is in the src/ directory.
"""

import os
import os.path
import platform
import shutil

import py
from py.compat import subprocess
from pypy.translator.cli.sdk import SDK
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

SRC_DIR = os.path.join(os.path.dirname(__file__), 'src/')

def _filename(name, path=None):
    rel_path =  os.path.join(SRC_DIR, name)
    return os.path.abspath(rel_path)

class Target:
    SOURCES = []
    OUTPUT = None
    ALIAS = None
    FLAGS = []
    DEPENDENCIES = []

    def get_COMPILER(cls):
        return SDK.csc()
    get_COMPILER = classmethod(get_COMPILER)
    
    def get(cls):
        for dep in cls.DEPENDENCIES:
            dep.get()
        sources = [_filename(src) for src in cls.SOURCES]
        out = _filename(cls.OUTPUT)
        alias = _filename(cls.ALIAS or cls.OUTPUT)
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
        os.chdir(SRC_DIR)
        compiler = subprocess.Popen([cls.get_COMPILER()] + cls.FLAGS + ['/out:%s' % out] + sources,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        retval = compiler.wait()
        assert retval == 0, 'Failed to compile %s: the compiler said:\n %s' % (cls.OUTPUT, stderr)
        if cls.ALIAS is not None:
            alias = _filename(cls.ALIAS)
            shutil.copy(out, alias)
        os.chdir(oldcwd)

    compile = classmethod(compile)

class MainStub(Target):
    SOURCES = ['stub/main.il']
    OUTPUT = 'main.exe'

    def get_COMPILER(cls):
        return SDK.ilasm()
    get_COMPILER = classmethod(get_COMPILER)
    
class FrameworkDLL(Target):
    SOURCES = ['pypylib.cs', 'll_os.cs', 'll_os_path.cs', 'errno.cs', 'll_math.cs']
    OUTPUT = 'pypylib.dll'
    ALIAS = 'pypylib-framework.dll'
    FLAGS = ['/t:library', '/unsafe', '/r:main.exe']
    DEPENDENCIES = [MainStub]

class UnixDLL(Target):
    SOURCES = ['pypylib.cs', 'll_os-unix.cs', 'll_math.cs']
    OUTPUT = 'pypylib.dll'
    ALIAS = 'pypylib-unix.dll'
    FLAGS = ['/t:library', '/unsafe', '/r:Mono.Posix', '/r:main.exe']
    DEPENDENCIES = [MainStub]

class Query(Target):
    SOURCES = ['query.cs']
    OUTPUT = 'query.exe'

    def compile(cls, sources, out):
        # assume that if query.exe need to be recompiled the descriptions cache is invalid        
        from pypy.translator.cli.query import _descfilename
        filename = _descfilename(None)
        if os.path.exists(filename):
            os.remove(filename)
        Target.compile.im_func(cls, sources, out)
    compile = classmethod(compile)

class Support(Target):
    SOURCES = ['support.cs']
    OUTPUT = 'support.dll'
    FLAGS = ['/t:library']

def get_pypy_dll():
    if os.environ.get('PYPYLIB', '').lower() == 'unix':
        DLL = UnixDLL
    else:
        DLL = FrameworkDLL
    return DLL.get()


if __name__ == '__main__':
    get_pypy_dll()
