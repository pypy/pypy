"""
Support for an automatically compiled Run Time Environment.
The source of the RTE is in the src/ directory.
"""

import os
import os.path
import subprocess

from pypy.translator.cli.sdk import SDK

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 


SRC = 'pypylib.cs'
DLL = 'pypylib.dll'

def _filename(name):
    rel_path = os.path.join(os.path.dirname(__file__), 'src/' + name)
    return os.path.abspath(rel_path)

def get_pypy_dll():
    source = _filename(SRC)
    dll = _filename(DLL)

    recompile = True
    try:
        source_stat = os.stat(source)
        dll_stat = os.stat(dll)
        if source_stat.st_mtime <= dll_stat.st_mtime:
            recompile = False
    except OSError:
        pass

    if recompile:
        compile(source, dll)

    return dll
    
def compile(source, dll):
    log.red("Compiling pypylib.dll")
    csc = SDK.csc()
    compiler = subprocess.Popen([csc, '/unsafe', '/t:library', '/out:%s' % dll, source],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = compiler.communicate()
    retval = compiler.wait()

    assert retval == 0, 'Failed to compile %s: the compiler said:\n %s' % (DLL, stderr)


if __name__ == '__main__':
    get_pypy_dll()
