class InvalidRawOperation(Exception):
    pass

class InvalidRawWrite(InvalidRawOperation):
    pass

class InvalidRawRead(InvalidRawOperation):
    pass

class RawBuffer(object):
    def __init__(self, cpu):
        # the following lists represents the writes in the buffer: values[i]
        # is the value of length lengths[i] stored at offset[i].
        #
        # the invariant is that they are ordered by offset, and that
        # offset[i]+length[i] <= offset[i+1], i.e. that the writes never
        # overlaps
        self.cpu = cpu
        self.offsets = []
        self.lengths = []
        self.descrs = []
        self.values = []

    def _get_memory(self):
        """
        NOT_RPYTHON
        for testing only
        """
        return zip(self.offsets, self.lengths, self.descrs, self.values)

    def _descrs_are_compatible(self, d1, d2):
        # two arraydescrs are compatible if they have the same basesize,
        # itemsize and sign, even if they are not identical
        unpack = self.cpu.unpack_arraydescr_size
        return unpack(d1) == unpack(d2)

    def write_value(self, offset, length, descr, value):
        i = 0
        N = len(self.offsets)
        while i < N:
            if self.offsets[i] == offset:
                if (length != self.lengths[i] or not
                    self._descrs_are_compatible(descr, self.descrs[i])):
                    # in theory we could add support for the cases in which
                    # the length or descr is different, but I don't think we
                    # need it in practice
                    raise InvalidRawWrite
                # update the value at this offset
                self.values[i] = value
                return
            elif self.offsets[i] > offset:
                break
            i += 1
        #
        if i < len(self.offsets) and offset+length > self.offsets[i]:
            raise InvalidRawWrite
        if i > 0 and self.offsets[i-1]+self.lengths[i-1] > offset:
            raise InvalidRawWrite
        # insert a new value at offset
        self.offsets.insert(i, offset)
        self.lengths.insert(i, length)
        self.descrs.insert(i, descr)
        self.values.insert(i, value)

    def read_value(self, offset, length, descr):
        i = 0
        N = len(self.offsets)
        while i < N:
            if self.offsets[i] == offset:
                if (length != self.lengths[i] or
                    not self._descrs_are_compatible(descr, self.descrs[i])):
                    raise InvalidRawRead
                return self.values[i]
            i += 1
        # memory location not found: this means we are reading from
        # uninitialized memory, give up the optimization
        raise InvalidRawRead
