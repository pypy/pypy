import sys

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rposix import OFF_T, get_saved_errno
from rpython.rlib.rarithmetic import r_longlong, widen

from pypy.interpreter.error import oefmt, wrap_oserror
from pypy.interpreter.gateway import unwrap_spec

_WIN32 = sys.platform == 'win32'

if not _WIN32:
    # _GNU_SOURCE: RWF_* flags and preadv2/pwritev2 are glibc extensions
    # declared in sys/uio.h only when this is defined.
    eci = ExternalCompilationInfo(
        includes=['sys/uio.h'],
        pre_include_bits=['#ifndef _GNU_SOURCE\n#define _GNU_SOURCE\n#endif'])

    class CConfig:
        _compilation_info_ = eci
        HAVE_PREADV = rffi_platform.Has('preadv')
        HAVE_PWRITEV = rffi_platform.Has('pwritev')
        HAVE_PREADV2 = rffi_platform.Has('preadv2')
        HAVE_PWRITEV2 = rffi_platform.Has('pwritev2')
        RWF_HIPRI = rffi_platform.DefinedConstantInteger('RWF_HIPRI')
        RWF_DSYNC = rffi_platform.DefinedConstantInteger('RWF_DSYNC')
        RWF_SYNC = rffi_platform.DefinedConstantInteger('RWF_SYNC')
        RWF_NOWAIT = rffi_platform.DefinedConstantInteger('RWF_NOWAIT')
        RWF_APPEND = rffi_platform.DefinedConstantInteger('RWF_APPEND')

    cConfig = rffi_platform.configure(CConfig)
    HAVE_PREADV = cConfig['HAVE_PREADV']
    HAVE_PWRITEV = cConfig['HAVE_PWRITEV']
    HAVE_PREADV2 = cConfig['HAVE_PREADV2']
    HAVE_PWRITEV2 = cConfig['HAVE_PWRITEV2']
    RWF_HIPRI = cConfig['RWF_HIPRI']
    RWF_DSYNC = cConfig['RWF_DSYNC']
    RWF_SYNC = cConfig['RWF_SYNC']
    RWF_NOWAIT = cConfig['RWF_NOWAIT']
    RWF_APPEND = cConfig['RWF_APPEND']

    IOVEC = rffi.CStruct('iovec', ('iov_base', rffi.VOIDP),
                          ('iov_len', rffi.SIZE_T))

    c_readv = rffi.llexternal(
        'readv', [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT], rffi.SSIZE_T,
        compilation_info=eci, save_err=rffi.RFFI_SAVE_ERRNO)
    c_writev = rffi.llexternal(
        'writev', [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT], rffi.SSIZE_T,
        compilation_info=eci, save_err=rffi.RFFI_SAVE_ERRNO)
    if HAVE_PREADV:
        c_preadv = rffi.llexternal(
            'preadv', [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT, OFF_T],
            rffi.SSIZE_T, compilation_info=eci,
            save_err=rffi.RFFI_SAVE_ERRNO)
    if HAVE_PWRITEV:
        c_pwritev = rffi.llexternal(
            'pwritev', [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT, OFF_T],
            rffi.SSIZE_T, compilation_info=eci,
            save_err=rffi.RFFI_SAVE_ERRNO)
    if HAVE_PREADV2:
        c_preadv2 = rffi.llexternal(
            'preadv2',
            [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT, OFF_T, rffi.INT],
            rffi.SSIZE_T, compilation_info=eci,
            save_err=rffi.RFFI_SAVE_ERRNO)
    if HAVE_PWRITEV2:
        c_pwritev2 = rffi.llexternal(
            'pwritev2',
            [rffi.INT, rffi.CArrayPtr(IOVEC), rffi.INT, OFF_T, rffi.INT],
            rffi.SSIZE_T, compilation_info=eci,
            save_err=rffi.RFFI_SAVE_ERRNO)

    def _acquire_buffers(space, w_buffers, writable):
        buffers_w = space.listview(w_buffers)
        n = len(buffers_w)
        views = [None] * n
        dummy_addr_len = (lltype.nullptr(rffi.VOIDP.TO), 0)
        addr_len_list = [dummy_addr_len] * n
        for i in range(n):
            w_buf = buffers_w[i]
            if writable:
                view, buf = space.acquire_writebuf(w_buf)
            else:
                view, buf = space.acquire_readbuf(w_buf)
            views[i] = view
            length = buf.getlength()
            if length == 0:
                addr = lltype.nullptr(rffi.VOIDP.TO)
            else:
                try:
                    addr = rffi.cast(rffi.VOIDP, buf.get_raw_address())
                except ValueError:
                    _release_buffers(views)
                    raise oefmt(space.w_TypeError,
                        "buffer %d does not support the buffer protocol "
                        "with a fixed memory address", i)
            addr_len_list[i] = (addr, length)
        return views, addr_len_list

    def _release_buffers(views):
        for view in views:
            if view is not None:
                view.releasebuffer()

    def _call_scatter_gather(space, fd, addr_len_list, c_func, offset):
        # offset == -1 is a sentinel for "no offset" (readv/writev): a real
        # offset is never negative, so this can't collide with a real call.
        n = len(addr_len_list)
        with lltype.scoped_alloc(rffi.CArray(IOVEC), max(n, 1)) as iovs:
            for i in range(n):
                addr, length = addr_len_list[i]
                iovs[i].c_iov_base = addr
                iovs[i].c_iov_len = rffi.cast(rffi.SIZE_T, length)
            if offset == -1:
                res = widen(c_func(fd, iovs, n))
            else:
                res = widen(c_func(fd, iovs, n, offset))
            if res < 0:
                raise OSError(get_saved_errno(), 'scatter/gather I/O failed')
            return res

    def _scatter_gather(space, fd, w_buffers, writable, c_func, offset):
        while True:
            views, addr_len_list = _acquire_buffers(space, w_buffers, writable)
            try:
                res = _call_scatter_gather(space, fd, addr_len_list, c_func,
                                            offset)
            except OSError as e:
                wrap_oserror(space, e, eintr_retry=True)
            else:
                return space.newint(res)
            finally:
                _release_buffers(views)

    def _call_scatter_gather_v2(space, fd, addr_len_list, c_func_v2, offset,
                                 flags):
        n = len(addr_len_list)
        with lltype.scoped_alloc(rffi.CArray(IOVEC), max(n, 1)) as iovs:
            for i in range(n):
                addr, length = addr_len_list[i]
                iovs[i].c_iov_base = addr
                iovs[i].c_iov_len = rffi.cast(rffi.SIZE_T, length)
            res = widen(c_func_v2(fd, iovs, n, offset, flags))
            if res < 0:
                raise OSError(get_saved_errno(), 'scatter/gather I/O failed')
            return res

    def _scatter_gather_v2(space, fd, w_buffers, writable, c_func_v2, offset,
                            flags):
        while True:
            views, addr_len_list = _acquire_buffers(space, w_buffers, writable)
            try:
                res = _call_scatter_gather_v2(space, fd, addr_len_list,
                                               c_func_v2, offset, flags)
            except OSError as e:
                wrap_oserror(space, e, eintr_retry=True)
            else:
                return space.newint(res)
            finally:
                _release_buffers(views)

    if HAVE_PREADV2:
        def _preadv_flags(space, fd, w_buffers, offset, flags):
            return _scatter_gather_v2(space, fd, w_buffers, True, c_preadv2,
                                       offset, flags)
    else:
        def _preadv_flags(space, fd, w_buffers, offset, flags):
            raise oefmt(space.w_NotImplementedError,
                        "preadv2() is not available on this platform")

    if HAVE_PWRITEV2:
        def _pwritev_flags(space, fd, w_buffers, offset, flags):
            return _scatter_gather_v2(space, fd, w_buffers, False, c_pwritev2,
                                       offset, flags)
    else:
        def _pwritev_flags(space, fd, w_buffers, offset, flags):
            raise oefmt(space.w_NotImplementedError,
                        "pwritev2() is not available on this platform")

    @unwrap_spec(fd="c_int")
    def readv(space, fd, w_buffers):
        """readv(fd, buffers) -> bytesread

        Read from a file descriptor fd into a number of writable buffers.
        buffers is an arbitrary sequence of writable buffers.
        Returns the total number of bytes read.
        """
        return _scatter_gather(space, fd, w_buffers, True, c_readv,
                                r_longlong(-1))

    @unwrap_spec(fd="c_int")
    def writev(space, fd, w_buffers):
        """writev(fd, buffers) -> byteswritten

        Write the contents of buffers to a file descriptor fd.
        buffers is an arbitrary sequence of buffers.
        Returns the total number of bytes written.
        """
        return _scatter_gather(space, fd, w_buffers, False, c_writev,
                                r_longlong(-1))

    if HAVE_PREADV:
        @unwrap_spec(fd="c_int", offset=r_longlong, flags=int)
        def preadv(space, fd, w_buffers, offset, flags=0):
            """preadv(fd, buffers, offset, flags=0) -> bytesread

            Read from a file descriptor fd at a given offset into a number
            of writable buffers. buffers is an arbitrary sequence of
            writable buffers. Returns the total number of bytes read.
            """
            if flags != 0:
                return _preadv_flags(space, fd, w_buffers, offset, flags)
            return _scatter_gather(space, fd, w_buffers, True, c_preadv,
                                    offset)

    if HAVE_PWRITEV:
        @unwrap_spec(fd="c_int", offset=r_longlong, flags=int)
        def pwritev(space, fd, w_buffers, offset, flags=0):
            """pwritev(fd, buffers, offset, flags=0) -> byteswritten

            Write the contents of buffers to a file descriptor fd at a
            given offset. buffers is an arbitrary sequence of buffers.
            Returns the total number of bytes written.
            """
            if flags != 0:
                return _pwritev_flags(space, fd, w_buffers, offset, flags)
            return _scatter_gather(space, fd, w_buffers, False, c_pwritev,
                                    offset)
