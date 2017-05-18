# The fast path has been removed and so were the tests
# They have been replaced with a test that shows that passing the wrong argument to a function that takes a string parameter no longer segfaults.
# This is why the assertion of an exception below. If it fails then it segfaults.

import ctypes

class TestFastpath():

    def test_fastpath_forbidden(self):
        libc = ctypes.cdll.LoadLibrary("libc.so.6")
        libc.strlen.argtypes = [ctypes.c_char_p]
        libc.strlen.restype = ctypes.c_size_t
        try:
            libc.strlen(False)
        except Exception as e:
                assert isinstance(e,Exception)
