
from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace
from rpython.rlib.rjitlog import rjitlog as jl

class AppTestJitLog(object):
    spaceconfig = {'usemodules': ['_jitlog', 'struct']}

    def setup_class(cls):
        cls.w_tmpfilename = cls.space.wrap(str(udir.join('test__jitlog.1')))
        cls.w_mark_header = cls.space.wrap(jl.MARK_JITLOG_HEADER)
        cls.w_version = cls.space.wrap(jl.JITLOG_VERSION_16BIT_LE)

    def test_enable(self):
        import _jitlog, struct
        tmpfile = open(self.tmpfilename, 'wb')
        fileno = tmpfile.fileno()
        _jitlog.enable(fileno)
        _jitlog.disable()
        # no need to clsoe tmpfile, it is done by jitlog

        with open(self.tmpfilename, 'rb') as fd:
            assert fd.read(1) == self.mark_header
            assert fd.read(2) == self.version
            count, = struct.unpack('<h', fd.read(2))
            for i in range(count):
                opnum = struct.unpack('<h', fd.read(2))
                strcount = struct.unpack('<i', fd.read(4))
                fd.read(strcount)
