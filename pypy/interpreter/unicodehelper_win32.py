from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rutf8 import codepoints_in_utf8
from rpython.rlib import rwin32

if rwin32.WIN32:
    def utf8_encode_mbcs(s, errors, errorhandler,
                            force_replace=True):
        lgt = codepoints_in_utf8(s)
        if not force_replace and errors not in ('strict', 'replace'):
            msg = "mbcs encoding does not support errors='%s'" % errors
            errorhandler('strict', 'mbcs', msg, s, 0, 0)

        if lgt == 0:
            return ''

        if force_replace or errors == 'replace':
            flags = 0
            used_default_p = lltype.nullptr(rwin32.BOOLP.TO)
        else:
            # strict
            flags = rwin32.WC_NO_BEST_FIT_CHARS
            used_default_p = lltype.malloc(rwin32.BOOLP.TO, 1, flavor='raw')
            used_default_p[0] = rffi.cast(rwin32.BOOL, False)

        try:
            with rffi.scoped_utf82wcharp(s, lgt) as dataptr:
                # first get the size of the result
                mbcssize = rwin32.WideCharToMultiByte(rwin32.CP_ACP, flags,
                                               dataptr, lgt, None, 0,
                                               None, used_default_p)
                if mbcssize == 0:
                    raise rwin32.lastSavedWindowsError()
                # If we used a default char, then we failed!
                if (used_default_p and
                    rffi.cast(lltype.Bool, used_default_p[0])):
                    errorhandler('strict', 'mbcs', "invalid character",
                                 s, 0, 0)

                with rffi.scoped_alloc_buffer(mbcssize) as buf:
                    # do the conversion
                    if rwin32.WideCharToMultiByte(rwin32.CP_ACP, flags,
                                           dataptr, lgt, buf.raw, mbcssize,
                                           None, used_default_p) == 0:
                        raise rwin32.lastSavedWindowsError()
                    if (used_default_p and
                        rffi.cast(lltype.Bool, used_default_p[0])):
                        errorhandler('strict', 'mbcs', "invalid character",
                                     s, 0, 0)
                    result = buf.str(mbcssize)
                    assert result is not None
                    return result
        finally:
            if used_default_p:
                lltype.free(used_default_p, flavor='raw')

    def is_dbcs_lead_byte(c):
        # XXX don't know how to test this
        return False

    def _decode_mbcs_error(s, errorhandler):
        if rwin32.GetLastError_saved() == rwin32.ERROR_NO_UNICODE_TRANSLATION:
            msg = ("No mapping for the Unicode character exists in the target "
                   "multi-byte code page.")
            errorhandler('strict', 'mbcs', msg, s, 0, 0)
        else:
            raise rwin32.lastSavedWindowsError()

    def default_unicode_error_decode(errors, encoding, msg, s,
                                     startingpos, endingpos):
        assert endingpos >= 0
        if errors == 'replace':
            return u'\ufffd', endingpos
        if errors == 'ignore':
            return u'', endingpos
        raise UnicodeDecodeError(encoding, s, startingpos, endingpos, msg)

    def str_decode_mbcs(s, size, errors, final=False, errorhandler=None,
                        force_ignore=True):
        size = len(s)
        if errorhandler is None:
            errorhandler = default_unicode_error_decode

        if not force_ignore and errors not in ('strict', 'ignore'):
            msg = "mbcs encoding does not support errors='%s'" % errors
            errorhandler('strict', 'mbcs', msg, s, 0, 0)

        if size == 0:
            return "", 0, 0

        if force_ignore or errors == 'ignore':
            flags = 0
        else:
            # strict
            flags = rwin32.MB_ERR_INVALID_CHARS

        # Skip trailing lead-byte unless 'final' is set
        if not final and is_dbcs_lead_byte(s[size-1]):
            size -= 1

        with rffi.scoped_nonmovingbuffer(s) as dataptr:
            # first get the size of the result
            usize = rwin32.MultiByteToWideChar(rwin32.CP_ACP, flags,
                                        dataptr, size,
                                        lltype.nullptr(rffi.CWCHARP.TO), 0)
            if usize == 0:
                _decode_mbcs_error(s, errorhandler)

            with rffi.scoped_alloc_unicodebuffer(usize) as buf:
                # do the conversion
                if rwin32.MultiByteToWideChar(rwin32.CP_ACP, flags,
                                       dataptr, size, buf.raw, usize) == 0:
                    _decode_mbcs_error(s, errorhandler)
                ret = buf.str(usize)
                assert ret is not None
                return ret.encode('utf-8'), usize, size


