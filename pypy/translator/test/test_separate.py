from pypy.translator.separate import export

class TestSeparate:
    def test_export(self):
        @export(int, float)
        def foo(x, y):
            pass
        @export(int, float, namespace='test')
        def bar(x, y):
            pass
        @export
        def baz():
            pass

        assert foo.argtypes == (int, float)
        assert not hasattr(foo, '_namespace_')
        assert bar.argtypes == (int, float)
        assert bar.namespace == 'test'
        assert not hasattr(baz, 'argtypes')
        assert baz.exported
