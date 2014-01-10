# Pulled from the shared test repo
from unipycation_shared.tests.base_test_uni import BaseTestUni
class AppTestUni(BaseTestUni):
    spaceconfig = dict(usemodules=('unipycation',))

    def setup_class(cls):
        space = cls.space
        (fd, fname) = tempfile.mkstemp(prefix="unipycation-")
        cls.w_fd = space.wrap(fd)
        cls.w_fname = space.wrap(fname)
