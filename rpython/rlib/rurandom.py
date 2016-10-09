"""The urandom() function, suitable for cryptographic use.
"""

from __future__ import with_statement
import os, sys
import errno

from rpython.rtyper.lltypesystem import lltype, rffi


if sys.platform == 'win32':
    from rpython.rlib import rwin32
    from rpython.translator.tool.cbuild import ExternalCompilationInfo
    from rpython.rtyper.tool import rffi_platform

    eci = ExternalCompilationInfo(
        includes = ['windows.h', 'wincrypt.h'],
        libraries = ['advapi32'],
        )

    class CConfig:
        _compilation_info_ = eci
        PROV_RSA_FULL = rffi_platform.ConstantInteger(
            "PROV_RSA_FULL")
        CRYPT_VERIFYCONTEXT = rffi_platform.ConstantInteger(
            "CRYPT_VERIFYCONTEXT")

    globals().update(rffi_platform.configure(CConfig))

    HCRYPTPROV = rwin32.ULONG_PTR

    CryptAcquireContext = rffi.llexternal(
        'CryptAcquireContextA',
        [rffi.CArrayPtr(HCRYPTPROV),
         rwin32.LPCSTR, rwin32.LPCSTR, rwin32.DWORD, rwin32.DWORD],
        rwin32.BOOL,
        calling_conv='win',
        compilation_info=eci,
        save_err=rffi.RFFI_SAVE_LASTERROR)

    CryptGenRandom = rffi.llexternal(
        'CryptGenRandom',
        [HCRYPTPROV, rwin32.DWORD, rffi.CArrayPtr(rwin32.BYTE)],
        rwin32.BOOL,
        calling_conv='win',
        compilation_info=eci,
        save_err=rffi.RFFI_SAVE_LASTERROR)

    def init_urandom():
        """NOT_RPYTHON
        Return an array of one HCRYPTPROV, initialized to NULL.
        It is filled automatically the first time urandom() is called.
        """
        return lltype.malloc(rffi.CArray(HCRYPTPROV), 1,
                             immortal=True, zero=True)

    def urandom(context, n):
        provider = context[0]
        if not provider:
            # This handle is never explicitly released. The operating
            # system will release it when the process terminates.
            if not CryptAcquireContext(
                context, None, None,
                PROV_RSA_FULL, CRYPT_VERIFYCONTEXT):
                raise rwin32.lastSavedWindowsError("CryptAcquireContext")
            provider = context[0]
        # TODO(win64) This is limited to 2**31
        with lltype.scoped_alloc(rffi.CArray(rwin32.BYTE), n,
                                 zero=True, # zero seed
                                 ) as buf:
            if not CryptGenRandom(provider, n, buf):
                raise rwin32.lastSavedWindowsError("CryptGenRandom")

            return rffi.charpsize2str(rffi.cast(rffi.CCHARP, buf), n)

elif 0:  # __VMS
    from rpython.rlib.ropenssl import libssl_RAND_pseudo_bytes
    def init_urandom():
        pass

    def urandom(context, n):
        with rffi.scoped_alloc_buffer(n) as buf:
            if libssl_RAND_pseudo_bytes(self.raw, n) < 0:
                raise ValueError("RAND_pseudo_bytes")
            return buf.str(n)
else:  # Posix implementation
    def init_urandom():
        """NOT_RPYTHON
        """
        return None

    def urandom(context, n):
        "Read n bytes from /dev/urandom."
        result = ''
        if n == 0:
            return result
        # XXX should somehow cache the file descriptor.  It's a mess.
        # CPython has a 99% solution and hopes for the remaining 1%
        # not to occur.  For now, we just don't cache the file
        # descriptor (any more... 6810f401d08e).
        fd = os.open("/dev/urandom", os.O_RDONLY, 0777)
        try:
            while n > 0:
                try:
                    data = os.read(fd, n)
                except OSError as e:
                    if e.errno != errno.EINTR:
                        raise
                    data = ''
                result += data
                n -= len(data)
        finally:
            os.close(fd)
        return result
