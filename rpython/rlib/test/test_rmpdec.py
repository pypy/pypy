from rpython.rlib import rmpdec

class TestMpdec:
    def test_constants(self):
        assert 'ROUND_HALF_EVEN' in rmpdec.ROUND_CONSTANTS
        assert isinstance(rmpdec.MPD_ROUND_HALF_EVEN, int)
