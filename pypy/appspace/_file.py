import sio

class file_(object):
    """An implementation of file objects in Python. it relies on Guido's
       sio.py implementation.
    """
    def __init__(self, filename, mode='r', bufsize=None):
        self.reading = False
        self.writing = False
        
        if not mode:
            raise IOError('invalid mode :  ')
        if mode[0] not in ['r', 'w', 'a', 'U']:
            raise IOError('invalid mode : %s' % mode)
        else:
            if mode[0] in ['r', 'U']:
                self.reading = True
            else:
                self.writing = True
        try:
            if mode[1] == 'b':
                plus = mode[2]
            else:
                plus = mode[1]
            if plus == '+':
                self.reading = self.writing = True
        except IndexError:
            pass
        
        self.fd = sio.DiskFile(filename, mode)
        if mode in ['U', 'rU']:
            # Wants universal newlines
            self.fd = sio.TextInputFilter(self.fd)
        if bufsize < 0:
            bufsize = None
        if not self.writing and (bufsize is None or bufsize > 0):
            self.fd = sio.BufferingInputStream(self.fd, bufsize)
        if not self.reading:
            if bufsize is None or bufsize > 1:
                self.fd = sio.BufferingOutputStream(self.fd, bufsize)
            elif bufsize == 1:
                self.fd = sio.LineBufferingOutputStream(self.fd)
        return self.fd

    def __getattr__(self, name):
        """
        Delegate all other methods to the underlying file object.
        """
        return getattr(self.fd, name)

    
