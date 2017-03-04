import errno
from rpython.rlib import rposix
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rposix import c_read
from rpython.rtyper.lltypesystem import lltype, rffi
from pypy.module._file.interp_file import is_wouldblock_error, signal_checker


def direct_readinto(self, w_rwbuffer):
    rwbuffer = self.space.writebuf_w(w_rwbuffer)
    stream = self.getstream()
    size = rwbuffer.getlength()
    target_address = lltype.nullptr(rffi.CCHARP.TO)
    fd = -1
    target_pos = 0

    if size > 64:
        try:
            target_address = rwbuffer.get_raw_address()
        except ValueError:
            pass
        else:
            fd = stream.try_to_find_file_descriptor()

    if fd < 0 or not target_address:
        # fall-back
        MAX_PART = 1024 * 1024    # 1 MB
        while size > MAX_PART:
            data = self.direct_read(MAX_PART)
            rwbuffer.setslice(target_pos, data)
            target_pos += len(data)
            size -= len(data)
            if len(data) != MAX_PART:
                break
        else:
            data = self.direct_read(size)
            rwbuffer.setslice(target_pos, data)
            target_pos += len(data)

    else:
        # optimized case: reading more than 64 bytes into a rwbuffer
        # with a valid raw address
        self.check_readable()

        # first "read" the part that is already sitting in buffers, if any
        initial_size = min(size, stream.count_buffered_bytes())
        if initial_size > 0:
            data = stream.read(initial_size)
            rwbuffer.setslice(target_pos, data)
            target_pos += len(data)
            size -= len(data)

        # then call c_read() to get the rest
        if size > 0:
            stream.flush()
            while True:
                got = c_read(fd, rffi.ptradd(target_address, target_pos), size)
                got = rffi.cast(lltype.Signed, got)
                if got > 0:
                    target_pos += got
                    size -= got
                    if size <= 0:
                        break
                elif got == 0:
                    break
                else:
                    err = rposix.get_saved_errno()
                    if err == errno.EINTR:
                        signal_checker(self.space)()
                        continue
                    if is_wouldblock_error(err) and target_pos > 0:
                        break
                    raise OSError(err, "read error")
            keepalive_until_here(rwbuffer)

    return self.space.newint(target_pos)
