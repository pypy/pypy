from hypothesis import given, strategies

def mean(a, b):
    return (a + b)/2.

@given(strategies.integers(), strategies.integers())
def test_mean_failing(a, b):
    assert mean(a, b) >= min(a, b)
