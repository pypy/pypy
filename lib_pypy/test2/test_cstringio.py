
"""
Tests for the PyPy cStringIO implementation.
"""

from pypy.conftest import gettestobjspace

class AppTestcStringIO:
    def setup_class(cls):
        cls.space = gettestobjspace()
        cls.w_io = cls.space.appexec([], "(): import cStringIO; return cStringIO")
        cls.w_bytes = cls.space.wrap('some bytes')


    def test_reset(self):
        """
        Test that the reset method of cStringIO objects sets the position
        marker to the beginning of the stream.
        """
        io = self.io.StringIO()
        io.write(self.bytes)
        assert io.read() == ''
        io.reset()
        assert io.read() == self.bytes

        io = self.io.StringIO(self.bytes)
        assert io.read() == self.bytes
        assert io.read() == ''
        io.reset()
        assert io.read() == self.bytes
