from pypy.conftest import gettestobjspace
from pypy.jit.metainterp.warmstate import JitCell

class AppTestJitInfo(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space
        cell = JitCell()
        cell.counter = 13
        w_code = space.appexec([], '''():
        def f():
           pass
        return f.func_code
        ''')
        w_code.jit_cells[13] = cell
        cls.w_code = w_code

    def test_getjitinfo(self):
        import pypyjit

        info = pypyjit.getjitinfo(self.code)
        assert info[13].counter == 13
        # assert did not crash

