import testsupport
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.objspace import StdObjSpace


class TestW_StringObject(testsupport.TestCase):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass
        

if __name__ == '__main__':
    testsupport.main()
