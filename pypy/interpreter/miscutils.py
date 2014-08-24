"""
Miscellaneous utilities.
"""

class ThreadLocals:
    """Pseudo thread-local storage, for 'space.threadlocals'.
    This is not really thread-local at all; the intention is that the PyPy
    implementation of the 'thread' module knows how to provide a real
    implementation for this feature, and patches 'space.threadlocals' when
    'thread' is initialized.
    """
    _value = None

    def get_ec(self):
        return self._value

    def enter_thread(self, space):
        self._value = space.createexecutioncontext()

    def try_enter_thread(self, space):
        return False

    def signals_enabled(self):
        return True

    def enable_signals(self, space):
        pass

    def disable_signals(self, space):
        pass

    def getallvalues(self):
        return {0: self._value}
