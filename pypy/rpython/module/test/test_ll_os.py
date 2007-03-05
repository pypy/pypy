import os
from pypy.tool.udir import udir
from pypy.tool.pytest.modcheck import skipimporterror
skipimporterror("ctypes")

from pypy.rpython.lltypesystem.module.ll_os import Implementation as impl
import sys

def test_access():
    filename = str(udir.join('test_access.txt'))
    rsfilename = impl.to_rstr(filename)

    fd = file(filename, 'w')
    fd.close()

    for mode in os.R_OK, os.W_OK, os.X_OK, os.R_OK | os.W_OK | os.X_OK:
        assert os.access(filename, mode) == impl.ll_os_access(rsfilename, mode)


def test_open_read_write_close():
    filename = str(udir.join('test_open_read_write_close.txt'))
    rsfilename = impl.to_rstr(filename)

    fd = impl.ll_os_open(rsfilename, os.O_WRONLY | os.O_CREAT, 0777)
    count = impl.ll_os_write(fd, impl.to_rstr("hello world\n"))
    assert count == len("hello world\n")
    impl.ll_os_close(fd)

    fd = impl.ll_os_open(rsfilename, os.O_RDONLY, 0777)
    data = impl.ll_os_read(fd, 500)
    assert impl.from_rstr(data) == "hello world\n"
    impl.ll_os_close(fd)

    os.unlink(filename)

def test_getcwd():
    data = impl.ll_os_getcwd()
    assert impl.from_rstr(data) == os.getcwd()

def test_strerror():
    data = impl.ll_os_strerror(2)
    assert impl.from_rstr(data) == os.strerror(2)

def test_system():
    filename = str(udir.join('test_system.txt'))
    arg = impl.to_rstr('python -c "print 1+1" > %s' % filename)
    data = impl.ll_os_system(arg)
    assert data == 0
    assert file(filename).read().strip() == '2'
    os.unlink(filename)

def test_putenv_unsetenv():
    filename = str(udir.join('test_putenv.txt'))
    arg = impl.to_rstr('abcdefgh=12345678')
    impl.ll_os_putenv(arg)
    cmd = '''python -c "import os; print os.environ['abcdefgh']" > %s''' % filename
    os.system(cmd)
    f = file(filename)
    result = f.read().strip()
    assert result == '12345678'
    f.close()
    os.unlink(filename)
    posix = __import__(os.name)
    if hasattr(posix, "unsetenv"):
        impl.ll_os_unsetenv(impl.to_rstr("abcdefgh"))
        cmd = '''python -c "import os; print repr(os.getenv('abcdefgh'))" > %s''' % filename
        os.system(cmd)
        f = file(filename)
        result = f.read().strip()
        assert result == 'None'
        f.close()
        os.unlink(filename)

test_src = """
import os
from pypy.tool.udir import udir
from pypy.rpython.lltypesystem.module.ll_os import Implementation as impl

def test_environ():
    count = 0
    while 1:
        if not impl.ll_os_environ(count):
            break
        count += 1
    channel.send(count == len(os.environ.keys()))
test_environ()
"""

def test_environ():
    import py
    gw = py.execnet.PopenGateway()
    chan = gw.remote_exec(py.code.Source(test_src))
    res = chan.receive()
    assert res
    chan.close()

def test_opendir_readdir():
    dirname = str(udir)
    rsdirname = impl.to_rstr(dirname)
    result = []
    DIR = impl.ll_os_opendir(rsdirname)
    try:
        while True:
            nextentry = impl.ll_os_readdir(DIR)
            if not nextentry:   # null pointer check
                break
            result.append(impl.from_rstr(nextentry))
    finally:
        impl.ll_os_closedir(DIR)
    assert '.' in result
    assert '..' in result
    result.remove('.')
    result.remove('..')
    result.sort()
    compared_with = os.listdir(dirname)
    compared_with.sort()
    assert result == compared_with

if hasattr(os, 'execv'):
    from pypy.rpython.extregistry import lookup
    os_execv = lookup(os.execv).lltypeimpl
    
    def test_execv():
        filename = str(udir.join('test_execv_ctypes.txt'))

        progname = str(sys.executable)
        l = ['', '']
        l[0] = progname
        l[1] = "-c"
        l.append('open("%s","w").write("1")' % filename)
        pid = os.fork()
        if pid == 0:
            os_execv(progname, l)
        else:
            os.waitpid(pid, 0)
        assert open(filename).read() == "1"

def test_dup():
    from pypy.rpython.extregistry import lookup
    os_dup = lookup(os.dup).lltypeimpl
    testf = udir.join('test.txt')
    testf.write("foo")
    path = testf.strpath

    def ff(fi):
        g = os_dup(fi)
        return g
    fi = os.open(path,os.O_RDONLY,0755)
    g = ff(fi)
    assert os.fstat(g) == os.fstat(fi)


