import autopath

class TestSysTests:
    def setup_method(self,method):
        self.sys_w = self.space.get_builtin_module("sys")
    def test_stdout_exists(self):
        s = self.space
        assert s.is_true(s.getattr(self.sys_w, s.wrap("stdout")))

class AppTestAppSysTests:
    def test_path_exists(self):
        import sys
        assert hasattr(sys, 'path'), "sys.path gone missing"
    def test_modules_exists(self):
        import sys
        assert hasattr(sys, 'modules'), "sys.modules gone missing"
    def test_dict_exists(self):
        import sys
        assert hasattr(sys, '__dict__'), "sys.__dict__ gone missing"
    def test_name_exists(self):
        import sys
        assert hasattr(sys, '__name__'), "sys.__name__ gone missing"
    def test_builtin_module_names_exists(self):
        import sys
        assert hasattr(sys, 'builtin_module_names'), (
                        "sys.builtin_module_names gone missing")        
    def test_warnoptions_exists(self):
        import sys
        assert hasattr(sys, 'warnoptions'), (
                        "sys.warnoptions gone missing")
    def test_hexversion_exists(self):
        import sys
        assert hasattr(sys, 'hexversion'), (
                        "sys.hexversion gone missing")
    def test_platform_exists(self):
        import sys
        assert hasattr(sys, 'platform'), "sys.platform gone missing"

    def test_sys_in_modules(self):
        import sys
        modules = sys.modules
        assert 'sys' in modules, ( "An entry for sys "
                                        "is not in sys.modules.")
        sys2 = sys.modules['sys']
        assert sys is sys2, "import sys is not sys.modules[sys]." 
    def test_builtin_in_modules(self):
        import sys
        modules = sys.modules
        assert '__builtin__' in modules, ( "An entry for __builtin__ "
                                                    "is not in sys.modules.")
        import __builtin__
        builtin2 = sys.modules['__builtin__']
        assert __builtin__ is builtin2, ( "import __builtin__ "
                                            "is not sys.modules[__builtin__].")
    def test_builtin_module_names(self):
        import sys
        names = sys.builtin_module_names
        assert 'sys' in names, (
                        "sys is not listed as a builtin module.")
        assert '__builtin__' in names, (
                        "__builtin__ is not listed as a builtin module.")

    def test_sys_exc_info(self):
        try:
            raise Exception
        except Exception,e:
            import sys
            exc_type,exc_val,tb = sys.exc_info()
        try:
            raise Exception   # 5 lines below the previous one
        except Exception,e2:
            exc_type2,exc_val2,tb2 = sys.exc_info()
        assert exc_type ==Exception
        assert exc_val ==e
        assert exc_type2 ==Exception
        assert exc_val2 ==e2
        assert tb2.tb_lineno - tb.tb_lineno == 5

    def test_exc_info_normalization(self):
        import sys
        try:
            1/0
        except ZeroDivisionError:
            etype, val, tb = sys.exc_info()
            assert isinstance(val, etype)
        else:
            raise AssertionError, "ZeroDivisionError not caught"
