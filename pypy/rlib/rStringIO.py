
PIECES = 80
BIGPIECES = 32

AT_END = -1


class RStringIO(object):
    """RPython-level StringIO object.
    The fastest path through this code is for the case of a bunch of write()
    followed by getvalue().  For at most PIECES write()s and one getvalue(),
    there is one copy of the data done, as if ''.join() was used.
    """
    _mixin_ = True        # for interp_stringio.py

    def __init__(self):
        # The real content is the join of the following data:
        #  * the list of characters self.bigbuffer;
        #  * each of the strings in self.strings.
        #
        # Invariants:
        #  * self.numbigstrings <= self.numstrings;
        #  * all strings in self.strings[self.numstrings:PIECES] are empty.
        #
        self.strings = [''] * PIECES
        self.numstrings = 0
        self.numbigstrings = 0
        self.bigbuffer = []
        self.pos = AT_END

    def close(self):
        self.strings = None
        self.numstrings = 0
        self.numbigstrings = 0
        self.bigbuffer = None

    def is_closed(self):
        return self.strings is None

    def getvalue(self):
        """If self.strings contains more than 1 string, join all the
        strings together.  Return the final single string."""
        if len(self.bigbuffer) > 0:
            self.copy_into_bigbuffer()
            return ''.join(self.bigbuffer)
        if self.numstrings > 1:
            result = self.strings[0] = ''.join(self.strings)
            for i in range(1, self.numstrings):
                self.strings[i] = ''
            self.numstrings = 1
            self.numbigstrings = 1
        else:
            result = self.strings[0]
        return result

    def getsize(self):
        result = len(self.bigbuffer)
        for i in range(0, self.numstrings):
            result += len(self.strings[i])
        return result

    def copy_into_bigbuffer(self):
        """Copy all the data into the list of characters self.bigbuffer."""
        for i in range(0, self.numstrings):
            self.bigbuffer += self.strings[i]
            self.strings[i] = ''
        self.numstrings = 0
        self.numbigstrings = 0
        return self.bigbuffer

    def reduce(self):
        """Reduce the number of (non-empty) strings in self.strings."""
        # When self.pos == AT_END, the calls to write(str) accumulate
        # the strings in self.strings until all PIECES slots are filled.
        # Then the reduce() method joins all the strings and put the
        # result back into self.strings[0].  The next time all the slots
        # are filled, we only join self.strings[1:] and put the result
        # in self.strings[1]; and so on.  The purpose of this is that
        # the string resulting from a join is expected to be big, so the
        # next join operation should only join the newly added strings.
        # When we have done this BIGPIECES times, the next join collects
        # all strings again into self.strings[0] and we start from
        # scratch.
        limit = self.numbigstrings
        self.strings[limit] = ''.join(self.strings[limit:])
        for i in range(limit + 1, self.numstrings):
            self.strings[i] = ''
        self.numstrings = limit + 1
        if limit < BIGPIECES:
            self.numbigstrings = limit + 1
        else:
            self.numbigstrings = 0
        assert self.numstrings <= BIGPIECES + 1
        return self.numstrings

    def write(self, buffer):
        # Idea: for the common case of a sequence of write() followed
        # by only getvalue(), self.bigbuffer remains empty.  It is only
        # used to handle the more complicated cases.
        p = self.pos
        if p != AT_END:    # slow or semi-fast paths
            assert p >= 0
            endp = p + len(buffer)
            if len(self.bigbuffer) >= endp:
                # semi-fast path: the write is entirely inside self.bigbuffer
                for i in range(len(buffer)):
                    self.bigbuffer[p+i] = buffer[i]
                self.pos = endp
                return
            else:
                # slow path: collect all data into self.bigbuffer and
                # handle the various cases
                bigbuffer = self.copy_into_bigbuffer()
                fitting = len(bigbuffer) - p
                if fitting > 0:
                    # the write starts before the end of the data
                    fitting = min(len(buffer), fitting)
                    for i in range(fitting):
                        bigbuffer[p+i] = buffer[i]
                    if len(buffer) > fitting:
                        # the write extends beyond the end of the data
                        bigbuffer += buffer[fitting:]
                        endp = AT_END
                    self.pos = endp
                    return
                else:
                    # the write starts at or beyond the end of the data
                    bigbuffer += '\x00' * (-fitting)
                    self.pos = AT_END      # fall-through to the fast path
        # Fast path.
        # See comments in reduce().
        count = self.numstrings
        if count == PIECES:
            count = self.reduce()
        self.strings[count] = buffer
        self.numstrings = count + 1

    def seek(self, position, mode=0):
        if mode == 1:
            if self.pos == AT_END:
                self.pos = self.getsize()
            position += self.pos
        elif mode == 2:
            if position == 0:
                self.pos = AT_END
                return
            position += self.getsize()
        if position < 0:
            position = 0
        self.pos = position

    def tell(self):
        if self.pos == AT_END:
            result = self.getsize()
        else:
            result = self.pos
        assert result >= 0
        return result

    def read(self, n=-1):
        p = self.pos
        if p == 0 and n < 0:
            self.pos = AT_END
            return self.getvalue()     # reading everything
        if p == AT_END:
            return ''
        assert p >= 0
        bigbuffer = self.copy_into_bigbuffer()
        mysize = len(bigbuffer)
        count = mysize - p
        if n >= 0:
            count = min(n, count)
        if count <= 0:
            return ''
        if p == 0 and count == mysize:
            self.pos = AT_END
            return ''.join(bigbuffer)
        else:
            self.pos = p + count
            return ''.join(bigbuffer[p:p+count])

    def truncate(self, size):
        # NB. 'size' is mandatory.  This has the same un-Posix-y semantics
        # than CPython: it never grows the buffer, and it sets the current
        # position to the end.
        assert size >= 0
        if size > len(self.bigbuffer):
            self.copy_into_bigbuffer()
        else:
            # we can drop all extra strings
            for i in range(0, self.numstrings):
                self.strings[i] = ''
            self.numstrings = 0
            self.numbigstrings = 0
        if size < len(self.bigbuffer):
            del self.bigbuffer[size:]
        self.pos = AT_END
