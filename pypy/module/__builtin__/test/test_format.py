class AppTestFormat:

    def test_format(self):
        """Test deprecation warnings from format(object(), 'nonempty')"""

        import warnings

        def test_deprecated(obj, fmt_str, should_raise_warning):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always", DeprecationWarning)
                format(obj, fmt_str)
            if should_raise_warning:
                assert len(w) == 1
                assert isinstance(w[0].message, DeprecationWarning)
                assert 'object.__format__ with a non-empty format string '\
                        in str(w[0].message)
            else:
                assert len(w) == 0

        fmt_strs = ['', 's']

        class A:
            def __format__(self, fmt_str):
                return format('', fmt_str)

        for fmt_str in fmt_strs:
            test_deprecated(A(), fmt_str, False)

        class B:
            pass

        class C(object):
            pass

        for cls in [object, B, C]:
            for fmt_str in fmt_strs:
                print(cls, fmt_str)
                test_deprecated(cls(), fmt_str, len(fmt_str) != 0)
