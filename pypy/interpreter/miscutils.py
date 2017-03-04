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
    _immutable_fields_ = ['_value?']
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

    def _cleanup_(self):
        # should still be unfilled at this point during translation.
        # but in some corner cases it is not...  unsure why
        self._value = None


def make_weak_value_dictionary(space, keytype, valuetype):
    "NOT_RPYTHON"
    if space.config.translation.rweakref:
        from rpython.rlib.rweakref import RWeakValueDictionary
        return RWeakValueDictionary(keytype, valuetype)
    else:
        class FakeWeakValueDict(object):
            def __init__(self):
                self._dict = {}
            def get(self, key):
                return self._dict.get(key, None)
            def set(self, key, value):
                self._dict[key] = value
        return FakeWeakValueDict()
