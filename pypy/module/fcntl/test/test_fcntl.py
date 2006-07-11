from py.test import raises, skip
from pypy.conftest import gettestobjspace

class AppTestFcntl:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('fcntl',))
        cls.space = space

    def test_conv_descriptor(self):
        import fcntl
        
        f = open("/tmp/conv_descr", "w")
        
        raises(TypeError, fcntl._conv_descriptor, "foo")
        raises(TypeError, fcntl._conv_descriptor, 2.0)
        import cStringIO
        raises(TypeError, fcntl._conv_descriptor, cStringIO.StringIO())
        res = fcntl._conv_descriptor(10)
        res_1 = fcntl._conv_descriptor(f)
        assert res == 10
        assert res_1 == f.fileno()

# def test_fcntl():
#     assert cfcntl.fcntl(f, 1, 0) == 0
#     assert cfcntl.fcntl(f, 2, "foo") == "foo"
#     py.test.raises(TypeError, cfcntl.fcntl, "foo")
#     py.test.raises(IOError, cfcntl.fcntl, -1, 1, 0)
# 
#     try:
#         os.O_LARGEFILE
#     except AttributeError:
#         start_len = "ll"
#     else:
#         start_len = "qq"
# 
#     if sys.platform in ('netbsd1', 'netbsd2', 'netbsd3', 
#                         'Darwin1.2', 'darwin',
#                         'freebsd2', 'freebsd3', 'freebsd4', 'freebsd5',
#                         'freebsd6', 'freebsd7', 
#                         'bsdos2', 'bsdos3', 'bsdos4',
#                         'openbsd', 'openbsd2', 'openbsd3'):
#         if struct.calcsize('l') == 8:
#             off_t = 'l'
#             pid_t = 'i'
#         else:
#             off_t = 'lxxxx'
#             pid_t = 'l'
# 
#         format = "%s%s%shh" % (off_t, off_t, pid_t)
#         lockdata = struct.pack(format, 0, 0, 0, cfcntl.F_WRLCK, 0)
#     else:
#         format = "hh%shh" % start_len
#         lockdata = struct.pack(format, cfcntl.F_WRLCK, 0, 0, 0, 0, 0)
# 
#     rv = cfcntl.fcntl(f.fileno(), cfcntl.F_SETLKW, lockdata)
#     assert rv == lockdata
#     assert cfcntl.fcntl(f, cfcntl.F_SETLKW, lockdata) == lockdata
# 
#     # test duplication of file descriptor
#     rv = cfcntl.fcntl(f, cfcntl.F_DUPFD)
#     assert rv > 2 # > (stdin, stdout, stderr) at least
#     assert cfcntl.fcntl(f, cfcntl.F_DUPFD) > rv
#     assert cfcntl.fcntl(f, cfcntl.F_DUPFD, 99) == 99
# 
#     # test descriptor flags
#     assert cfcntl.fcntl(f, cfcntl.F_GETFD) == 0
#     cfcntl.fcntl(f, cfcntl.F_SETFD, 1)
#     assert cfcntl.fcntl(f, cfcntl.F_GETFD, cfcntl.FD_CLOEXEC) == 1
# 
#     # test status flags
#     assert cfcntl.fcntl(f.fileno(), cfcntl.F_SETFL, os.O_NONBLOCK) == 0
#     assert cfcntl.fcntl(f.fileno(), cfcntl.F_SETFL, os.O_NDELAY) == 0
#     assert cfcntl.fcntl(f, cfcntl.F_SETFL, os.O_NONBLOCK) == 0
#     assert cfcntl.fcntl(f, cfcntl.F_SETFL, os.O_NDELAY) == 0
# 
#     if "linux" in sys.platform:
#         # test managing signals
#         assert cfcntl.fcntl(f, cfcntl.F_GETOWN) == 0
#         cfcntl.fcntl(f, cfcntl.F_SETOWN, 20)
#         assert cfcntl.fcntl(f, cfcntl.F_GETOWN) == 20
#         assert cfcntl.fcntl(f, cfcntl.F_GETSIG) == 0
#         cfcntl.fcntl(f, cfcntl.F_SETSIG, 20)
#         assert cfcntl.fcntl(f, cfcntl.F_GETSIG) == 20
# 
#         # test leases
#         assert cfcntl.fcntl(f, cfcntl.F_GETLEASE) == cfcntl.F_UNLCK
#         cfcntl.fcntl(f, cfcntl.F_SETLEASE, cfcntl.F_WRLCK)
#         assert cfcntl.fcntl(f, cfcntl.F_GETLEASE) == cfcntl.F_WRLCK
#     else:
#         # this tests should fail under BSD
#         # with "Inappropriate ioctl for device"
#         py.test.raises(IOError, cfcntl.fcntl, f, cfcntl.F_GETOWN)
#         py.test.raises(IOError, cfcntl.fcntl, f, cfcntl.F_SETOWN, 20)
# 
# 
# def test_flock():
#     if "linux" in sys.platform:
#         cfcntl.flock(f, cfcntl.LOCK_SH)
#         # this is an error EWOULDBLOCK, man: The file is locked and the
#         # LOCK_NB flag was selected.
#         py.test.raises(IOError, cfcntl.flock, f, cfcntl.LOCK_NB)
#         py.test.raises(IOError, cfcntl.flock, f, 3)
#     py.test.raises(TypeError, cfcntl.flock, f, "foo")
#     cfcntl.flock(f, cfcntl.LOCK_UN)
# 
# def test_lockf():
#     py.test.raises(TypeError, cfcntl.lockf, f, "foo")
#     py.test.raises(TypeError, cfcntl.lockf, f, cfcntl.LOCK_UN, "foo")
#     py.test.raises(ValueError, cfcntl.lockf, f, 0)
# 
# def test_ioctl():
#     py.test.raises(TypeError, cfcntl.ioctl, "foo")
#     py.test.raises(TypeError, cfcntl.ioctl, 0, "foo")
#     py.test.raises(TypeError, cfcntl.ioctl, 0, termios.TIOCGPGRP, float(0))
#     py.test.raises(TypeError, cfcntl.ioctl, 0, termios.TIOCGPGRP, 1, "foo")
# 
#     buf = array.array('h', [0])
#     assert cfcntl.ioctl(0, termios.TIOCGPGRP, buf, True) == 0
#     buf = array.array('c', "a"*1025)
#     py.test.raises(ValueError, cfcntl.ioctl, 0, termios.TIOCGPGRP, buf, 0)
#     py.test.raises(ValueError, cfcntl.ioctl, 0, termios.TIOCGPGRP,
#                    "a"*1025, 0)
