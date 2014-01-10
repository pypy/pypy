# Pulled from the shared test repo
from unipycation_shared.tests import base_test_uni

class AppTestUni(base_test_uni.BaseTestUni):
    spaceconfig = dict(usemodules=('unipycation',))

    def setup_class(cls):
        import tempfile
        space = cls.space
        (fd, fname) = tempfile.mkstemp(prefix="unipycation-")
        cls.w_fd = space.wrap(fd)
        cls.w_fname = space.wrap(fname)

class AppTestUniRevCall(base_test_uni.BaseTestUniRevCall):
    spaceconfig = dict(usemodules=('unipycation',))

