
""" Some more binascii.py tests
"""

class AppTestBinAscii:
    def test_incorrect_padding(self):
        import binascii
        raises(binascii.Error, "'x'.decode('base64')")
