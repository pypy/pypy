from pypy.module.test_lib_pypy.support import import_lib_pypy


class AppTestGrp:
    spaceconfig = dict(usemodules=('binascii', '_rawffi', 'itertools'))

    def setup_class(cls):
        cls.w_grp = import_lib_pypy(cls.space, 'grp',
                                    "No grp module on this platform")

    def test_basic(self):
        raises(KeyError, self.grp.getgrnam, "dEkLofcG")
        for name in ["root", "wheel"]:
            try:
                g = self.grp.getgrnam(name)
            except KeyError:
                continue
            assert g.gr_gid == 0
            assert 'root' in g.gr_mem or g.gr_mem == []
            assert g.gr_name == name
            assert isinstance(g.gr_passwd, str)    # usually just 'x', don't hope :-)
            break
        else:
            raise

    def test_extra(self):
        grp = self.grp
        print(grp.__file__)
        raises(TypeError, grp.getgrnam, False)
        raises(TypeError, grp.getgrnam, None)

    def test_struct_group(self):
        g = self.grp.struct_group((10, 20, 30, 40))
        assert len(g) == 4
        assert list(g) == [10, 20, 30, 40]
        assert g.gr_name == 10
        assert g.gr_passwd == 20
        assert g.gr_gid == 30
        assert g.gr_mem == 40
