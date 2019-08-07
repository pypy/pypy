import struct


class SandboxError(Exception):
    """The sandboxed process misbehaved"""


class Ptr(object):
    def __init__(self, addr):
        self.addr = addr

    def __repr__(self):
        return 'Ptr(%s)' % (hex(self.addr),)


_ptr_size = struct.calcsize("P")
_ptr_code = 'q' if _ptr_size == 8 else 'i'
_pack_one_ptr = struct.Struct("=" + _ptr_code).pack
_pack_one_longlong = struct.Struct("=q").pack
_pack_one_double = struct.Struct("=d").pack
_pack_two_ptrs = struct.Struct("=" + _ptr_code + _ptr_code).pack
_unpack_one_ptr = struct.Struct("=" + _ptr_code).unpack


class SandboxedIO(object):
    _message_decoders = {}


    def __init__(self, popen):
        self.popen = popen
        self.child_stdin = popen.stdin
        self.child_stdout = popen.stdout

    def close(self):
        """Kill the subprocess and close the file descriptors to the pipe.
        """
        if self.popen.returncode is None:
            self.popen.terminate()
        self.child_stdin.close()
        self.child_stdout.close()

    def _read(self, count):
        result = self.child_stdout.read(count)
        if len(result) != count:
            raise SandboxError(
                "connection interrupted with the sandboxed process")
        return result

    @staticmethod
    def _make_message_decoder(data):
        i1 = data.find('(')
        i2 = data.find(')')
        if not (i1 > 0 and i1 < i2 and i2 == len(data) - 2):
            raise SandboxError(
                "badly formatted data received from the sandboxed process")
        pack_args = ['=']
        for c in data[i1+1:i2]:
            if c == 'p':
                pack_args.append(_ptr_code)
            elif c == 'i':
                pack_args.append('q')
            elif c == 'f':
                pack_args.append('d')
            elif c == 'v':
                pass
            else:
                raise SandboxError(
                    "unsupported format string in parentheses: %r" % (data,))
        unpacker = struct.Struct(''.join(pack_args))
        decoder = unpacker, data[i1+1:i2]

        SandboxedIO._message_decoders[data] = decoder
        return decoder

    def read_message(self):
        """Wait for the next message and returns it.  Raises EOFError if the
        subprocess finished.  Raises SandboxError if there is another kind
        of detected misbehaviour.
        """
        ch = self.child_stdout.read(1)
        if len(ch) == 0:
            raise EOFError
        n = ord(ch)
        msg = self._read(n)
        decoder = self._message_decoders.get(msg)
        if decoder is None:
            decoder = self._make_message_decoder(msg)

        unpacker, codes = decoder
        raw_args = iter(unpacker.unpack(self._read(unpacker.size)))
        args = []
        for c in codes:
            if c == 'p':
                args.append(Ptr(next(raw_args)))
            elif c == 'v':
                args.append(None)
            else:
                args.append(next(raw_args))
        return msg, args

    def read_buffer(self, ptr, length):
        g = self.child_stdin
        g.write("R" + _pack_two_ptrs(ptr.addr, length))
        g.flush()
        return self._read(length)

    def read_charp(self, ptr, maxlen=-1):
        g = self.child_stdin
        g.write("Z" + _pack_two_ptrs(ptr.addr, maxlen))
        g.flush()
        length = _unpack_one_ptr(self._read(_ptr_size))[0]
        return self._read(length)

    def write_buffer(self, ptr, bytes_data):
        g = self.child_stdin
        g.write("W" + _pack_two_ptrs(ptr.addr, len(bytes_data)))
        g.write(bytes_data)
        # g.flush() not necessary here

    def write_result(self, result):
        g = self.child_stdin
        if result is None:
            g.write('v')
        elif isinstance(result, Ptr):
            g.write('p' + _pack_one_ptr(result.addr))
        elif isinstance(result, float):
            g.write('f' + _pack_one_double(result))
        else:
            g.write('i' + _pack_one_longlong(result))
        g.flush()
