class _ALWAYS_EQ:
    """
    Object that is equal to anything.
    """
    def __eq__(self, other):
        return True
    def __ne__(self, other):
        return False

ALWAYS_EQ = _ALWAYS_EQ()

class _NEVER_EQ:
    """
    Object that is not equal to anything.
    """
    def __eq__(self, other):
        return False
    def __ne__(self, other):
        return True

NEVER_EQ = _NEVER_EQ()


def test_contains_list():
    assert not ALWAYS_EQ in [NEVER_EQ,]

def test_contains_tuple():
    assert not ALWAYS_EQ in (NEVER_EQ,)
