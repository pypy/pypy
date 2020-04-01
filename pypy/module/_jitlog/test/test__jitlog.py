import sys
import platform
from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace
from rpython.rlib.rjitlog import rjitlog as jl
from rpython.jit.metainterp.resoperation import opname
from rpython.rlib.rfile import c_fopen, c_fileno
from pypy.interpreter import gateway

class AppTestJitLog(object):
    spaceconfig = {'usemodules': ['_jitlog', 'struct']}

    def setup_class(cls):
        cls.w_tmpfilename = cls.space.wrap(str(udir.join('test__jitlog.1')))
        cls.w_mark_header = cls.space.newbytes(jl.MARK_JITLOG_HEADER)
        cls.w_version = cls.space.newbytes(jl.JITLOG_VERSION_16BIT_LE)
        cls.w_is_32bit = cls.space.wrap(sys.maxint == 2**31-1)
        cls.w_machine = cls.space.newbytes(platform.machine())
        cls.w_resops = cls.space.newdict()
        space = cls.space
        for key, value in opname.items():
            space.setitem(cls.w_resops, space.wrap(key), space.wrap(value))
        if cls.runappdirect:
            def open_returnfd(space, w_name, w_mode):
                fid = open(w_name, w_mode)
                return fid.fileno()
            cls.w_open_returnfd = open_returnfd
        else:
            def open_returnfd(space, w_name, w_mode):
                name = space.text_w(w_name)
                mode = space.text_w(w_mode)
                fid = c_fopen(name, mode)
                fd = c_fileno(fid)
                return space.newint(fd)
            cls.w_open_returnfd = space.wrap(gateway.interp2app(open_returnfd))

    def test_enable(self):
        import _jitlog, struct
        # use c_fopen instead of file.open since the host python and compiled
        # code may use different runtime libraries (win32 visual2008 vs.
        # visual2019 for instance. No error checking
        fileno = self.open_returnfd(self.tmpfilename, 'wb')
        _jitlog.enable(fileno)
        _jitlog.disable()
        # no need to close tmpfilename, it is done by jitlog

        with open(self.tmpfilename, 'rb') as fd:
            assert fd.read(1) == self.mark_header
            assert fd.read(2) == self.version
            assert bool(ord(fd.read(1))) == self.is_32bit
            strcount, = struct.unpack('<i', fd.read(4))
            machine = fd.read(strcount)
            assert machine == self.machine
            # resoperations
            count, = struct.unpack('<h', fd.read(2))
            opnames = set()
            for i in range(count):
                opnum = struct.unpack('<h', fd.read(2))
                strcount, = struct.unpack('<i', fd.read(4))
                opname = fd.read(strcount)
                opnames.append((opnum, opname))

            for opnum, opname in opnames:
                # must be known resoperation
                assert opnum in self.resops
                # the name must equal
                assert self.resops[opnum] == opname
