from pypy.tool.logparser import *

def test_gettotaltimes():
    result = gettotaltimes([
        ('foo', 2, 17, [
            ('bar', 4, 5, []),
            ('bar', 7, 9, []),
            ]),
        ('bar', 20, 30, []),
        ])
    assert result == {None: 3,              # the hole between 17 and 20
                      'foo': 15 - 1 - 2,
                      'bar': 1 + 2 + 10}
