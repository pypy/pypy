class AppTestCodeModule:

    def w_get_interp(self):
        import code
        import io
        class MockedInterpreter(code.InteractiveInterpreter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.out = io.StringIO()

            def write(self, data):
                self.out.write(data)
        return MockedInterpreter()

    def test_cause_tb(self):
        interp = self.get_interp()
        interp.runsource('raise IOError from OSError')
        result = interp.out.getvalue()
        expected_header = """OSError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
"""
        assert expected_header in result
        assert result.endswith("IOError\n")

    def test_context_tb(self):
        interp = self.get_interp()
        interp.runsource("""\
try: zzzeek
except: _diana_
""")
        result = interp.out.getvalue()
        expected_header = """NameError: name 'zzzeek' is not defined

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
"""
        assert expected_header in result
        assert result.endswith("NameError: name '_diana_' is not defined\n")
