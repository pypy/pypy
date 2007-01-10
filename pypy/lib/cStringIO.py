#
# StringIO-based cStringIO implementation.
#

from StringIO import *
from StringIO import __doc__

class StringIO(StringIO):
    def reset(self):
        """
        reset() -- Reset the file position to the beginning
        """
        self.seek(0, 0)
