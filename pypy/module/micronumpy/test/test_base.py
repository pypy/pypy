from pypy.conftest import gettestobjspace


class BaseNumpyAppTest(object):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=('micronumpy',))