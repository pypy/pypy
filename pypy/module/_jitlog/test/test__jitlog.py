
from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace

class AppTestJitLog(object):
    spaceconfig = {'usemodules': ['_jitlog']}

    def setup_class(cls):
        cls.w_tmpfilename = cls.space.wrap(str(udir.join('test__jitlog.1')))

    def test_enable(self):
        import _jitlog
        tmpfile = open(self.tmpfilename, 'wb')
        fileno = tmpfile.fileno()
        _jitlog.enable(fileno)
        _jitlog.disable()
        # no need to clsoe tmpfile, it is done by jitlog
