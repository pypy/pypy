import unittest
import testsupport
from pypy.interpreter.pyframe_app import decode_frame_arguments

class CodeObject:
    """ A code object class for test purposes. """
    def __init__(self, count=3, vflag = 0, kflag = 0):
        self.co_argcount = count
        self.co_varnames = ('a', 'b', 'c', 'd', 'e')
        self.co_flags = 4 * vflag + 8 * kflag


class Testdecode_frame_arguments(unittest.TestCase):
    
    def test_plain_parameters(self):
        self.assertEqual(
            (1, 2, 3, (4,)),
            decode_frame_arguments((1, 2, 3, 4), {}, (), None,
                                   CodeObject(vflag=1)))

    def test_non_used_keyword(self):
        self.assertEqual(
            (1, 2, 3, (4,), {'e':0}),
            decode_frame_arguments((1, 2, 3, 4), {'e':0}, (), None,
                                   CodeObject(vflag=1, kflag=1)))

    def test_used_keyword(self):
        self.assertEqual(
            (1, 2, 10, ()),
            decode_frame_arguments((1, 2), {'c':10}, (20,), None,
                                   CodeObject(vflag=1)))

    def test_mixed_keyword(self):
        self.assertEqual(
            (1, 2, 10, (), {'e':30}),
            decode_frame_arguments((1, 2), {'c':10, 'e':30}, (20,), None,
                                   CodeObject(vflag=1, kflag=1)))

    def test_used_default(self):
        self.assertEqual(
            (1, 2, 20),
            decode_frame_arguments((1, 2), {}, (20,), None, CodeObject()))

    def test_no_varargs(self):
        self.assertEqual(
            (20, 30, 40),
            decode_frame_arguments((), {}, (20, 30, 40), None, CodeObject()))

    def test_no_args(self):
        self.assertEqual(
            (),
            decode_frame_arguments((), {}, (), None, CodeObject(count=0)))

    def test_fail_keywords_has_bad_formal_parameter(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (1, 2, 3), {'xxx':666}, (), None, CodeObject())

    def test_fail_too_many_parameters(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (1, 2, 3, 4, 5, 6), {}, (), None, CodeObject())

    def test_fail_not_enough_parameters(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (), {}, (), None, CodeObject())

    def test_fail_extra_no_varargs(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (1, 2, 3, 4), {}, (20,), None, CodeObject(vflag=0))

    def test_fail_setting_parameter_twice_with_extra_actual_keyword(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (1, 2, 3, 4), {'a':666, 'b':666}, (), None, CodeObject())

    def test_fail_setting_parameter_twice_with_extra_formal_keyword(self):
        self.assertRaises(
            TypeError,
            decode_frame_arguments,
            (1, 2, 3, 4), {}, (), None, CodeObject(kflag=1))
        
if __name__ == "__main__":
    unittest.main()   
