import sio

class file_(object):
    """An implementation of file objects in Python. it relies on Guido's
       sio.py implementation.
    """

    
    def __init__(self, name, mode='r', bufsize=None):
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

        self._mode = mode
        self._name = name
        self._closed = False
        self.softspace =  0 # Required according to file object docs
        self._encoding = None # Fix when we find out how encoding should be
        self.fd = sio.DiskFile(name, mode)
        if mode in ['U', 'rU']:
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

    def __getattr__(self, attr):
        """
        Handle the readonly attributes and then delegate the other
        methods to the underlying file object, setting the 'closed'
        attribute if you close the file.
        """
        if attr in ['fd', 'softspace', 'reading', 'writing']:
            return self.__dict__[attr]
        elif attr in ['mode', 'name', 'closed', 'encoding']:
            return self.__dict__['_' + attr]
        elif attr == 'close':
            self._closed = True
                
        return getattr(self.fd, attr)

    def __setattr__(self, attr, val):
        "Make some attributes readonly."
        if attr in ['mode', 'name', 'closed', 'encoding']:
            raise TypeError, "readonly attribute:'%s'" % attr
        self.__dict__[attr] = val
