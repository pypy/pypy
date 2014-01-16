# Pulled from the shared test repo
from unipycation_shared.tests.base_test_coreengine import BaseTestCoreEngine
class AppTestCoreEngine(BaseTestCoreEngine):
    spaceconfig = dict(usemodules=('unipycation',))

    def setup_class(cls):
        import tempfile
        space = cls.space
        (fd, fname) = tempfile.mkstemp(prefix="unipycation-")
        cls.w_fd = space.wrap(fd)
        cls.w_fname = space.wrap(fname)
