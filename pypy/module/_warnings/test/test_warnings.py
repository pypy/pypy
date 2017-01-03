class AppTestWarnings:
    spaceconfig = dict(usemodules=('_warnings',))

    def test_defaults(self):
        import _warnings
        assert _warnings._onceregistry == {}
        assert _warnings._defaultaction == 'default'
        expected = [('ignore', None, DeprecationWarning, None, 0),
                    ('ignore', None, PendingDeprecationWarning, None, 0),
                    ('ignore', None, ImportWarning, None, 0),
                    ('ignore', None, BytesWarning, None, 0),
                    ('ignore', None, ResourceWarning, None, 0)]
        assert expected == _warnings.filters

    def test_warn(self):
        import _warnings
        _warnings.warn("some message", DeprecationWarning)
        _warnings.warn("some message", Warning)
        _warnings.warn(("some message",1), Warning)

    def test_use_builtin__warnings(self):
        """Check that the stdlib warnings.py module manages to import our
        _warnings module.  If something is missing, it doesn't, and silently
        continues.  Then things don't reliably work: either the
        functionality of the pure Python version is subtly different, or
        more likely we get confusion because of a half-imported _warnings.
        """
        import warnings
        assert not hasattr(warnings, '_filters_version')

    def test_lineno(self):
        import warnings, _warnings, sys
        with warnings.catch_warnings(record=True) as w:
            _warnings.warn("some message", Warning)
            lineno = sys._getframe().f_lineno - 1 # the line above
            assert w[-1].lineno == lineno

    def test_warn_explicit(self):
        import _warnings
        _warnings.warn_explicit("some message", DeprecationWarning,
                                "<string>", 1, module_globals=globals())
        _warnings.warn_explicit("some message", Warning,
                                "<string>", 1, module_globals=globals())

    def test_default_action(self):
        import warnings, _warnings
        warnings.defaultaction = 'ignore'
        warnings.resetwarnings()
        with warnings.catch_warnings(record=True) as w:
            __warningregistry__ = {}
            _warnings.warn_explicit("message", UserWarning, "<test>", 44,
                                    registry={})
            assert len(w) == 0
        warnings.defaultaction = 'default'

    def test_show_source_line(self):
        import warnings
        import sys, io
        try:
            from test.warning_tests import inner
        except ImportError:
            skip('no test, -A on cpython?')
        # With showarning() missing, make sure that output is okay.
        del warnings.showwarning

        stderr = sys.stderr
        try:
            sys.stderr = io.StringIO()
            inner('test message')
            result = sys.stderr.getvalue()
        finally:
            sys.stderr = stderr

        assert result.count('\n') == 2
        assert '  warnings.warn(message, ' in result

    def test_filename_none(self):
        import _warnings
        globals()['__file__'] = 'test.pyc'
        _warnings.warn('test', UserWarning)
        globals()['__file__'] = None
        _warnings.warn('test', UserWarning)
