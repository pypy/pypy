import testsupport

class TestStdObjectSpace(testsupport.TestCase):

    def setUp(self):
        self.space = testsupport.objspace()

    def tearDown(self):
        pass

    def test_newstring(self):
        w = self.space.wrap
        s = 'abc'
        chars_w = [w(ord(c)) for c in s]
        self.assertEqual_w(w(s), self.space.newstring(chars_w))

    def test_newstring_fail(self):
        w = self.space.wrap
        s = 'abc'
        not_chars_w = [w(c) for c in s]
        self.assertRaises_w(self.space.w_TypeError,
                            self.space.newstring,
                            not_chars_w)
        self.assertRaises_w(self.space.w_ValueError,
                            self.space.newstring,
                            [w(-1)])

if __name__ == '__main__':
    testsupport.main()
