from pypy.tool.pytest.appsupport import app_hypothesis_given
import hypothesis.strategies as strategies


# test for the app-test hypothesis support

@app_hypothesis_given(strategies.floats(min_value=1.0, max_value=2.0))
def app_test_floats(f):
    assert 1.0 <= f <= 2.0
    assert f == f # not a NaN


