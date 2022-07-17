import pytest
import sys

# not an applevel test: errno is not preserved
class TestMsvcrt:
    if sys.platform != 'win32':
        pytest.skip("only on Windows")

    def test_locking(self, tmpdir):
        filename = tmpdir / 'locking_test'
        filename.ensure()

        import os, msvcrt, errno

        fd = os.open(str(filename), 0)
        try:
            msvcrt.locking(fd, 1, 1)

            # lock again: it fails
            with pytest.raises(IOError) as e:
                msvcrt.locking(fd, 1, 1)
            assert e.value.errno == errno.EDEADLOCK

            # unlock and relock sucessfully
            msvcrt.locking(fd, 0, 1)
            msvcrt.locking(fd, 1, 1)
        finally:
            os.close(fd)

    def test_getch(self):
        import msvcrt
        with pytest.raises(TypeError):
            msvcrt.ungetch('a')
        msvcrt.ungetch(b'a')
        k = msvcrt.getch()
        assert k == b'a'

    def test_getwch(self):
        import msvcrt
        msvcrt.ungetwch('a')
        k = msvcrt.getwch()
        assert k == u'a'
