
import py

class AppTestHashLib:
    def setup_class(cls):
        from pypy.conftest import option, gettestobjspace
        if option.runappdirect:
            try:
                import __pypy__
            except ImportError:
                py.test.skip("Whitebox tests")
        cls.space = gettestobjspace(usemodules=('_rawffi','struct'))

    
    def test_unicode(self):
        import hashlib
        import _hashlib
        assert isinstance(hashlib.new('sha1', u'xxx'), _hashlib.hash)

