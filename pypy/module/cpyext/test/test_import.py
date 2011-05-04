from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.rpython.lltypesystem import rffi, lltype

class TestImport(BaseApiTest):
    def test_import(self, space, api):
        pdb = api.PyImport_Import(space.wrap("pdb"))
        assert pdb
        assert space.getattr(pdb, space.wrap("pm"))

    def test_addmodule(self, space, api):
        with rffi.scoped_str2charp("sys") as modname:
            w_sys = api.PyImport_AddModule(modname)
        assert w_sys is space.sys

        with rffi.scoped_str2charp("foobar") as modname:
            w_foobar = api.PyImport_AddModule(modname)
        assert space.str_w(space.getattr(w_foobar,
                                         space.wrap('__name__'))) == 'foobar'

    def test_reload(self, space, api):
        pdb = api.PyImport_Import(space.wrap("pdb"))
        space.delattr(pdb, space.wrap("set_trace"))
        pdb = api.PyImport_ReloadModule(pdb)
        assert space.getattr(pdb, space.wrap("set_trace"))

class AppTestImportLogic(AppTestCpythonExtensionBase):
    def test_import_logic(self):
        skip("leak?")
        path = self.import_module(name='test_import_module', load_it=False)
        import sys
        sys.path.append(path)
        import test_import_module
        assert test_import_module.TEST is None

