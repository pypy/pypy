class AppTestWarnings:
    spaceconfig = dict(usemodules=('_warnings',))

    def test_defaults(self):
        import _warnings
        assert _warnings.once_registry == {}
        assert _warnings.default_action == 'default'
        assert "PendingDeprecationWarning" in str(_warnings.filters)

    def test_warn(self):
        import _warnings
        _warnings.warn("some message", DeprecationWarning)
        _warnings.warn("some message", Warning)
        _warnings.warn(("some message",1), Warning)

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
        import sys, StringIO
        try:
            from test.warning_tests import inner
        except ImportError:
            skip('no test, -A on cpython?')
        # With showarning() missing, make sure that output is okay.
        saved = warnings.showwarning
        try:
            del warnings.showwarning

            stderr = sys.stderr
            try:
                sys.stderr = StringIO.StringIO()
                inner('test message')
                result = sys.stderr.getvalue()
            finally:
                sys.stderr = stderr

            assert result.count('\n') == 2
            assert '  warnings.warn(message, ' in result
        finally:
            warnings.showwarning = saved

    def test_filename_none(self):
        import _warnings
        globals()['__file__'] = 'test.pyc'
        _warnings.warn('test', UserWarning)
        globals()['__file__'] = None
        _warnings.warn('test', UserWarning)

    def test_warn_unicode(self):
        import _warnings, sys
        old = sys.stderr
        try:
            class Grab:
                def write(self, u):
                    self.data.append(u)
            sys.stderr = Grab()
            sys.stderr.data = data = []
            _warnings.warn_explicit("9238exbexn8", Warning,
                                    "<string>", 1421, module_globals=globals())
            assert isinstance(''.join(data), str)
            _warnings.warn_explicit(u"\u1234\u5678", UserWarning,
                                    "<str2>", 831, module_globals=globals())
            assert isinstance(''.join(data), unicode)
            assert ''.join(data).endswith(
                             u'<str2>:831: UserWarning: \u1234\u5678\n')
        finally:
            sys.stderr = old

    def test_issue31285(self):
        import _warnings
        def get_bad_loader(splitlines_ret_val):
            class BadLoader:
                def get_source(self, fullname):
                    class BadSource(str):
                        def splitlines(self):
                            return splitlines_ret_val
                    return BadSource('spam')
            return BadLoader()
        # does not raise:
        _warnings.warn_explicit(
            'eggs', UserWarning, 'bar', 1,
            module_globals={'__loader__': get_bad_loader(42),
                            '__name__': 'foobar'})

