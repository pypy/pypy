from _pytest.monkeypatch import monkeypatch
from rpython.tool import ansi_print


class FakeOutput(object):
    def __init__(self, tty=True):
        self.monkey = monkeypatch()
        self.tty = tty
        self.output = []
    def __enter__(self, *args):
        self.monkey.setattr(ansi_print, 'ansi_print', self._print)
        self.monkey.setattr(ansi_print, 'isatty', self._isatty)
        return self.output
    def __exit__(self, *args):
        self.monkey.undo()

    def _print(self, text, colors):
        self.output.append((text, colors))
    def _isatty(self):
        return self.tty


def test_simple():
    log = ansi_print.Logger('test')
    with FakeOutput() as output:
        log('Hello')
    assert output == [('[test] Hello', ())]

def test_bold():
    log = ansi_print.Logger('test')
    with FakeOutput() as output:
        log.bold('Hello')
    assert output == [('[test] Hello', (1,))]

def test_not_a_tty():
    log = ansi_print.Logger('test')
    with FakeOutput(tty=False) as output:
        log.bold('Hello')
    assert output == [('[test] Hello', ())]
