import sio

class file_(object):
    """An implementation of file objects in Python. it relies on Guido's
       sio.py implementation.
    """
    def __init__(self, filename, filemode='r', bufsize=None):
        self.reading = False
        self.writing = False
        
        if not filemode:
            raise IOError('invalid mode :  ')
        if filemode[0] not in ['r', 'w', 'a', 'U']:
            raise IOError('invalid mode : %s' % filemode)
        else:
            if filemode[0] in ['r', 'U']:
                self.reading = True
            else:
                self.writing = True
        try:
            if filemode[1] == 'b':
                plus = filemode[2]
            else:
                plus = filemode[1]
            if plus == '+':
                self.reading = self.writing = True
        except IndexError:
            pass

        self.filemode = filemode
        self.filename = filename
        self.isclosed = False
        self.softspace =  0 # Required according to file object docs 
        self.fd = sio.DiskFile(filename, filemode)
        if filemode in ['U', 'rU']:
            # Wants universal newlines
            self.fd = sio.TextInputFilter(self.fd)
        if bufsize < 0:
            bufsize = None
        if not self.writing and (bufsize is None or bufsize > 0):
            "Read only buffered stream."
            self.fd = sio.BufferingInputStream(self.fd, bufsize)
        if not self.reading:
            if bufsize is None or bufsize > 1:
                "Write only buffered stream."
                self.fd = sio.BufferingOutputStream(self.fd, bufsize)
            elif bufsize == 1:
                self.fd = sio.LineBufferingOutputStream(self.fd)
        if self.reading and self.writing:
            if bufsize > 2:
                "Read and write buffered stream."
                self.fd = sio.BufferingInputOutputStream(self.fd, bufsize)
        return self.fd

    def __getattr__(self, attr):
        """
        Delegate all methods to the underlying file object.
        """
        if attr == 'close':
            self.isclosed = True
        
        return getattr(self.fd, attr)

    def __setattr__(self, attr, val):
        "Make some attributes readonly."
        if attr in ['mode', 'name', 'closed', 'encoding']:
            raise TypeError('readonly attribute: %s' % attr)
        self.__dict__[attr] = val
