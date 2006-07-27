"""
Support for an automatically compiled Run Time Environment.
The source of the RTE is in the src/ directory.
"""

import os
import os.path
import platform
import subprocess
import shutil

from pypy.translator.cli.sdk import SDK

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

def _filename(name):
    rel_path = os.path.join(os.path.dirname(__file__), 'src/' + name)
    return os.path.abspath(rel_path)

class DLL:
    def get(cls):
        sources = [_filename(src) for src in cls.SOURCES]
        dll = _filename(cls.DLL)
        recompile = True
        try:
            src_mtime = max([os.stat(src).st_mtime for src in sources])
            dll_mtime = os.stat(dll).st_mtime
            if src_mtime <= dll_mtime:
                recompile = False
        except OSError:
            pass

        if recompile:
            cls.compile(sources, dll)
        return dll
    get = classmethod(get)

    def compile(cls, sources, dll):
        log.red("Compiling %s" % cls.DLL)
        csc = SDK.csc()
        compiler = subprocess.Popen([csc] + cls.FLAGS + ['/t:library', '/out:%s' % dll] + sources,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = compiler.communicate()
        retval = compiler.wait()
        assert retval == 0, 'Failed to compile %s: the compiler said:\n %s' % (DLL, stderr)
    compile = classmethod(compile)


class FrameworkDLL(DLL):
    SOURCES = ['pypylib.cs', 'll_os.cs']
    DLL = 'pypylib-framework.dll'
    FLAGS = ['/unsafe']

class UnixDLL(DLL):
    SOURCES = ['pypylib.cs', 'll_os-unix.cs']
    DLL = 'pypylib-unix.dll'
    FLAGS = ['/unsafe', '/r:Mono.Posix']


def get_pypy_dll():
    dll = _filename('pypylib.dll')
    if platform.system() == 'Windows':
        dll_orig = FrameworkDLL.get()
    else:
        dll_orig = UnixDLL.get()
    shutil.copy(dll_orig, dll)
    return dll

if __name__ == '__main__':
    if platform.system() != 'Windows':
        shutil.copy(UnixDLL.get(), '.')
    shutil.copy(FrameworkDLL.get(), '.')
