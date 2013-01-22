import py


def braindead_deindent(self):
    """monkeypatch that wont end up doing stupid in the python tokenizer"""
    text = '\n'.join(self.lines)
    short = py.std.textwrap.dedent(text)
    newsource = py.code.Source()
    newsource.lines[:] = short.splitlines()
    return newsource


def pytest_configure():
    py.code.Source.deindent = braindead_deindent


def pytest_pycollect_makeitem(__multicall__,collector, name, obj):
    res = __multicall__.execute()
    # work around pytest issue 251
    import inspect
    if res is None and inspect.isclass(obj) and \
            collector.classnamefilter(name):
        return py.test.collect.Class(name, parent=collector)
    return res
