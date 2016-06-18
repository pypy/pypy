import py
import os, sys


def build(tmpdir):
    import cffi
    ffibuilder = cffi.FFI()

    ffibuilder.cdef("""
        int ancil_send_fds(int, const int *, unsigned);
        int ancil_recv_fds(int, int *, unsigned);
    """)

    local_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(local_dir, 'src-revdb')

    ffibuilder.set_source("_ancillary_cffi", """
        #include <ancillary.h>
    """, include_dirs=[src_dir],
         sources=[os.path.join(src_dir, 'fd_send.c'),
                  os.path.join(src_dir, 'fd_recv.c')])

    ffibuilder.compile(tmpdir=tmpdir, verbose=True)

def import_(verbose=False):
    import rpython
    basedir = py.path.local(rpython.__file__).dirpath()
    tmpdir = str(basedir.ensure('_cache', 'ancillary', dir=1))
    if verbose:
        print tmpdir
    old_sys_path = sys.path[:]
    sys.path.insert(0, tmpdir)
    try:
        import _ancillary_cffi
    except ImportError:
        build(tmpdir)
        import _ancillary_cffi
    sys.path[:] = old_sys_path
    return _ancillary_cffi.ffi, _ancillary_cffi.lib


def send_fds(pipe_num, fd_list):
    ffi, lib = import_()
    if lib.ancil_send_fds(pipe_num, fd_list, len(fd_list)) < 0:
        raise OSError(ffi.errno, "ancil_send_fds() failed")

def recv_fds(pipe_num, fd_count):
    ffi, lib = import_()
    p = ffi.new("int[]", fd_count)
    result = lib.ancil_recv_fds(pipe_num, p, fd_count)
    if result < 0:
        raise OSError(ffi.errno, "ancil_recv_fds() failed")
    return [p[i] for i in xrange(result)]


if __name__ == '__main__':
    import_(verbose=True)
