# test the integration of unicode and strings (even though we don't
# really implement unicode yet).

import autopath, sys


objspacename = 'std'

class AppTestFakedTypes:
    def test_inheriting(self):
        class MyUnicode(unicode):
            pass
        my_u = MyUnicode('123')
        assert type(my_u) is MyUnicode
