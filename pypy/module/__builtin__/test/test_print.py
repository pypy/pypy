class AppTestPrint:

    def test_print_flush(self):
        """
        # operation of the flush flag
        class filelike():
            def __init__(self):
                self.written = ''
                self.flushed = 0
            def write(self, str):
                self.written += str
            def flush(self):
                self.flushed += 1

        f = filelike()
        print(1, file=f, end='', flush=True)
        print(2, file=f, end='', flush=True)
        print(3, file=f, flush=False)
        assert f.written == '123\\n'
        assert f.flushed == 2

        # ensure exceptions from flush are passed through
        class noflush():
            def write(self, str):
                pass
            def flush(self):
                raise RuntimeError
        raises(RuntimeError, print, 1, file=noflush(), flush=True)
        """
