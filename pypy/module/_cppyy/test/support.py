import py, sys, subprocess

currpath = py.path.local(__file__).dirpath()


def setup_make(targetname):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    import pypy.module._cppyy.capi.loadable_capi as lcapi
    popen = subprocess.Popen(["make", targetname], cwd=str(currpath),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = popen.communicate()
    if popen.returncode:
        if '-std=c++11' in stdout:
            py.test.skip("gcc does not seem to support -std=c++11")
        raise OSError("'make' failed:\n%s" % (stdout,))
