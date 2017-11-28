import pytest
from rpython.rlib.rvmprof.test.support import FakeVMProf

class TestFakeVMProf(object):

    def test_sampling(self):
        fake = FakeVMProf()
        assert not fake.is_sampling_enabled
        #
        fake.start_sampling()
        assert fake.is_sampling_enabled
        #
        fake.stop_sampling()
        fake.stop_sampling()
        assert not fake.is_sampling_enabled
        #
        fake.start_sampling()
        assert not fake.is_sampling_enabled
        fake.start_sampling()
        assert fake.is_sampling_enabled
        #
        pytest.raises(AssertionError, "fake.start_sampling()")
    
