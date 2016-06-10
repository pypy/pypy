from pypy.tool.pytest.appsupport import app_hypothesis_given
import hypothesis.strategies as strategies


# test for the app-test hypothesis support

@app_hypothesis_given(strategies.floats(min_value=1.0, max_value=2.0))
def app_test_floats(f):
    assert 1.0 <= f <= 2.0
    assert f == f # not a NaN

@app_hypothesis_given(strategies.floats(min_value=1.0, max_value=2.0), strategies.floats(min_value=1.0, max_value=3.0))
def app_test_2_floats(f, g):
    assert 1.0 <= f <= 2.0
    assert 1.0 <= g <= 3.0
    assert f == f # not a NaN
    assert g == g # not a NaN

class AppTest(object):
    @app_hypothesis_given(strategies.floats(min_value=1.0, max_value=2.0))
    def test_floats(self, f):
        assert 1.0 <= f <= 2.0
        assert f == f # not a NaN
