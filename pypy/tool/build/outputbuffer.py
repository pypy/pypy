try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class OutputBuffer(object):
    def __init__(self, print_channel=None):
        self.print_channel = print_channel
        self.buffer = StringIO()

    def write(self, s):
        self.buffer.write(s)
        if self.print_channel:
            self.print_channel.write(s)
            if hasattr(self.print_channel, 'flush'):
                self.print_channel.flush()

    def getvalue(self):
        return self.buffer.getvalue()

    def isatty(self):
        return False

