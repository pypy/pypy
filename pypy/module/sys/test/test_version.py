class AppTestVersion:
    def test_compiler(self):
        import sys
        assert ("MSC v." in sys.version or
                "GCC " in sys.version)

def test_get_version(space, monkeypatch):
    from pypy.module.sys import version
    monkeypatch.setattr(version, 'PYPY_VERSION', (2,5,0, "final", 1))
    res = space.unwrap(version.get_version(space))
    assert "[PyPy 2.5.0" in res
    monkeypatch.setattr(version, 'PYPY_VERSION', (2,6,3, "alpha", 5))
    res = space.unwrap(version.get_version(space))
    assert "[PyPy 2.6.3-alpha5" in res
