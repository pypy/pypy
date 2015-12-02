class AppTestVersion:
    def test_compiler(self):
        import sys
        assert ("MSC v." in sys.version or
                "GCC " in sys.version or
                "(untranslated)" in sys.version)

def test_get_version():
    from pypy.module.sys import version
    res = version._make_version_template(PYPY_VERSION=(2,5,0, "final", 1))
    assert "[PyPy 2.5.0" in res
    res = version._make_version_template(PYPY_VERSION=(2,6,3, "alpha", 5))
    assert "[PyPy 2.6.3-alpha5" in res
    assert res.endswith(' with %s]')
