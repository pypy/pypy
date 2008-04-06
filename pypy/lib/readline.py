"""A compatibility wrapper reimplementing the 'readline' standard module
on top of pyrepl.  Not all functionalities are supported.
"""

import sys, os

ENCODING = 'latin1'     # XXX hard-coded

# ____________________________________________________________

class _ReaderMixin(object):
    readline_completer = None
    completer_delims = dict.fromkeys(' \t\n`~!@#$%^&*()-=+[{]}\\|;:\'",<>/?')

    def get_stem(self):
        b = self.buffer
        p = self.pos - 1
        while p >= 0 and b[p] not in self.completer_delims:
            p -= 1
        return ''.join(b[p+1:self.pos])

    def get_completions(self, stem):
        result = []
        function = self.readline_completer
        if function is not None:
            try:
                stem = str(stem)   # rlcompleter.py seems to not like unicode
            except UnicodeEncodeError:
                pass   # but feed unicode anyway if we have no choice
            state = 0
            while True:
                next = function(stem, state)
                if not isinstance(next, str):
                    break
                result.append(next)
                state += 1
        return result

    def get_trimmed_history(self, maxlength):
        if maxlength >= 0:
            cut = len(self.history) - maxlength
            if cut < 0:
                cut = 0
        else:
            cut = 0
        return self.history[cut:]

# ____________________________________________________________

class _ReadlineWrapper(object):
    f_in = 0
    f_out = 1
    reader = None
    saved_history_length = -1
    startup_hook = None

    def get_reader(self):
        if self.reader is None:
            from pyrepl.historical_reader import HistoricalReader
            from pyrepl.completing_reader import CompletingReader
            from pyrepl.unix_console import UnixConsole
            class MyReader(_ReaderMixin, HistoricalReader, CompletingReader):
                pass
            console = UnixConsole(self.f_in, self.f_out, encoding=ENCODING)
            self.reader = MyReader(console)
        return self.reader

    def raw_input(self, prompt=''):
        reader = self.get_reader()
        if self.startup_hook is not None:
            self.startup_hook()
        reader.ps1 = prompt
        return reader.readline()

    def parse_and_bind(self, string):
        pass  # XXX we don't support parsing GNU-readline-style init files

    def set_completer(self, function=None):
        self.get_reader().readline_completer = function

    def get_completer(self):
        return self.get_reader().readline_completer

    def set_completer_delims(self, string):
        self.get_reader().completer_delims = dict.fromkeys(string)

    def get_completer_delims(self):
        chars = self.get_reader().completer_delims.keys()
        chars.sort()
        return ''.join(chars)

    def _histline(self, line):
        return unicode(line.rstrip('\n'), ENCODING)

    def get_history_length(self):
        return self.saved_history_length

    def set_history_length(self, length):
        self.saved_history_length = length

    def get_current_history_length(self):
        return len(self.get_reader().history)

    def read_history_file(self, filename='~/.history'):
        history = self.get_reader().history
        f = open(os.path.expanduser(filename), 'r')
        for line in f:
            history.append(self._histline(line))
        f.close()

    def write_history_file(self, filename='~/.history'):
        maxlength = self.saved_history_length
        history = self.get_reader().get_trimmed_history(maxlength)
        f = open(os.path.expanduser(filename), 'w')
        for entry in history:
            if isinstance(entry, unicode):
                entry = entry.encode(ENCODING)
            f.write(entry + '\n')
        f.close()

    def clear_history(self):
        del self.get_reader().history[:]

    def get_history_item(self, index):
        history = self.get_reader().history
        if 1 <= index <= len(history):
            return history[index-1]
        else:
            return None        # blame readline.c for not raising

    def remove_history_item(self, pos):
        history = self.get_reader().history
        if 1 <= index <= len(history):
            del history[index-1]
        else:
            raise ValueError("No history item at position %d" % index)
            # blame readline.c for raising ValueError

    def replace_history_item(self, pos, line):
        history = self.get_reader().history
        if 1 <= index <= len(history):
            history[index-1] = self._histline(line)
        else:
            raise ValueError("No history item at position %d" % index)
            # blame readline.c for raising ValueError

    def add_history(self, line):
        self.get_reader().history.append(self._histline(line))

    def set_startup_hook(self, function=None):
        self.startup_hook = function

_wrapper = _ReadlineWrapper()

# ____________________________________________________________
# Public API

parse_and_bind = _wrapper.parse_and_bind
set_completer = _wrapper.set_completer
get_completer = _wrapper.get_completer
set_completer_delims = _wrapper.set_completer_delims
get_completer_delims = _wrapper.get_completer_delims
get_history_length = _wrapper.get_history_length
set_history_length = _wrapper.set_history_length
get_current_history_length = _wrapper.get_current_history_length
read_history_file = _wrapper.read_history_file
write_history_file = _wrapper.write_history_file
clear_history = _wrapper.clear_history
get_history_item = _wrapper.get_history_item
remove_history_item = _wrapper.remove_history_item
replace_history_item = _wrapper.replace_history_item
add_history = _wrapper.add_history
set_startup_hook = _wrapper.set_startup_hook

# ____________________________________________________________
# Stubs

def _make_stub(_name, _ret):
    def stub(*args, **kwds):
        import warnings
        warnings.warn("readline.%s() not implemented" % _name, stacklevel=2)
    stub.func_name = _name
    globals()[_name] = stub

for _name, _ret in [
    ('get_line_buffer', ''),
    ('insert_text', None),
    ('read_init_file', None),
    ('redisplay', None),
    ('set_pre_input_hook', None),
    ('get_begidx', 0),
    ('get_endidx', 0),
    ]:
    assert _name not in globals(), _name
    _make_stub(_name, _ret)

# ____________________________________________________________

def _setup():
    try:
        import _curses
    except ImportError:
        try:
            import _minimal_curses
        except ImportError:
            raise ImportError("readline.py needs a minimal curses module")
        sys.modules['_curses'] = _minimal_curses

    try:
        f_in = sys.stdin.fileno()
        f_out = sys.stdout.fileno()
    except AttributeError:
        return
    if not os.isatty(f_in) or not os.isatty(f_out):
        return

    _wrapper.f_in = f_in
    _wrapper.f_out = f_out

    if hasattr(sys, '__raw_input__'):    # PyPy
        sys.__raw_input__ = _wrapper.raw_input
    else:
        # this is not really what readline.c does.  Better than nothing I guess
        import __builtin__
        __builtin__.raw_input = _wrapper.raw_input

_setup()

if __name__ == '__main__':    # for testing
    import __main__
    sys.modules['readline'] = __main__
    if os.getenv('PYTHONSTARTUP'):
        execfile(os.getenv('PYTHONSTARTUP'))
    import code
    code.interact()
