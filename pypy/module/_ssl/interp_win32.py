from rpython.rlib import rwin32
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import wrap_windowserror
from rpython.rlib.rarithmetic import intmask
eci = ExternalCompilationInfo(
    includes = ['windows.h', 'wincrypt.h'],
    libraries = ['crypt32'],
)

class CConfig:
    _compilation_info_ = eci

    X509_ASN_ENCODING = rffi_platform.ConstantInteger('X509_ASN_ENCODING')
    PKCS_7_ASN_ENCODING = rffi_platform.ConstantInteger('PKCS_7_ASN_ENCODING')
    CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG = rffi_platform.ConstantInteger('CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG')
    CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG = rffi_platform.ConstantInteger('CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG')
    CRYPT_E_NOT_FOUND = rffi_platform.ConstantInteger('CRYPT_E_NOT_FOUND')

    CERT_ENHKEY_USAGE = rffi_platform.Struct(
        'CERT_ENHKEY_USAGE', [('cUsageIdentifier', rwin32.DWORD),
                              ('rgpszUsageIdentifier', rffi.CCHARPP)])
    CERT_CONTEXT = rffi_platform.Struct(
        'CERT_CONTEXT', [('pbCertEncoded', rffi.CCHARP),
                         ('cbCertEncoded', rwin32.DWORD),
                         ('dwCertEncodingType', rwin32.DWORD)])
    CRL_CONTEXT = rffi_platform.Struct(
        'CRL_CONTEXT', [('pbCrlEncoded', rffi.CCHARP),
                        ('cbCrlEncoded', rwin32.DWORD),
                        ('dwCertEncodingType', rwin32.DWORD)])

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

PCERT_ENHKEY_USAGE = lltype.Ptr(CERT_ENHKEY_USAGE)
PCCERT_CONTEXT = lltype.Ptr(CERT_CONTEXT)
PCCRL_CONTEXT = lltype.Ptr(CRL_CONTEXT)

def external(name, argtypes, restype, **kw):
    kw['compilation_info'] = eci
    kw['calling_conv'] = 'win'
    kw['save_err'] = rffi.RFFI_SAVE_LASTERROR
    return rffi.llexternal(
        name, argtypes, restype, **kw)

CertOpenSystemStore = external(
    'CertOpenSystemStoreA', [rffi.VOIDP, rffi.CCHARP], rwin32.HANDLE)
CertCloseStore = external(
    'CertCloseStore', [rwin32.HANDLE, rwin32.DWORD], rwin32.BOOL)
CertGetEnhancedKeyUsage = external(
    'CertGetEnhancedKeyUsage',
    [PCCERT_CONTEXT, rwin32.DWORD, PCERT_ENHKEY_USAGE, rwin32.LPDWORD],
    rwin32.BOOL)
CertEnumCertificatesInStore = external(
    'CertEnumCertificatesInStore',
    [rwin32.HANDLE, PCCERT_CONTEXT], PCCERT_CONTEXT)
CertFreeCertificateContext = external(
    'CertFreeCertificateContext', [PCCERT_CONTEXT], rwin32.BOOL)
CertEnumCRLsInStore = external(
    'CertEnumCRLsInStore',
    [rwin32.HANDLE, PCCRL_CONTEXT], PCCRL_CONTEXT)
CertFreeCRLContext = external(
    'CertFreeCRLContext', [PCCRL_CONTEXT], rwin32.BOOL)

def w_certEncodingType(space, encodingType):
    if encodingType == X509_ASN_ENCODING:
        return space.newtext("x509_asn")
    elif encodingType == PKCS_7_ASN_ENCODING:
        return space.newtext("pkcs_7_asn")
    else:
        return space.newint(encodingType)

def w_parseKeyUsage(space, pCertCtx, flags):
    with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as size_ptr:
        if not CertGetEnhancedKeyUsage(pCertCtx, flags,
                             lltype.nullptr(CERT_ENHKEY_USAGE), size_ptr):
            last_error = rwin32.lastSavedWindowsError()
            if last_error.winerror == CRYPT_E_NOT_FOUND:
                return space.w_True
            raise wrap_windowserror(space, last_error)

        size = intmask(size_ptr[0])
        with lltype.scoped_alloc(rffi.CCHARP.TO, size) as buf:
            usage = rffi.cast(PCERT_ENHKEY_USAGE, buf)
            # Now get the actual enhanced usage property
            if not CertGetEnhancedKeyUsage(pCertCtx, flags, usage, size_ptr):
                last_error= rwin32.lastSavedWindowsError()
                if last_error.winerror == CRYPT_E_NOT_FOUND:
                    return space.w_True
                raise wrap_windowserror(space, last_error)

            result_w = [None] * usage.c_cUsageIdentifier
            for i in range(usage.c_cUsageIdentifier):
                if not usage.c_rgpszUsageIdentifier[i]:
                    continue
                result_w[i] = space.newtext(rffi.charp2str(
                    usage.c_rgpszUsageIdentifier[i]))
            return space.newset(result_w)

@unwrap_spec(store_name='text')
def enum_certificates_w(space, store_name):
    """enum_certificates(store_name) -> []

    Retrieve certificates from Windows' cert store. store_name may be one of
    'CA', 'ROOT' or 'MY'. The system may provide more cert storages, too.
    The function returns a list of (bytes, encoding_type, trust) tuples. The
    encoding_type flag can be interpreted with X509_ASN_ENCODING or
    PKCS_7_ASN_ENCODING. The trust setting is either a set of OIDs or the
    boolean True."""

    result_w = []
    pCertCtx = lltype.nullptr(CERT_CONTEXT)
    hStore = CertOpenSystemStore(None, store_name)
    if not hStore:
        raise wrap_windowserror(space, rwin32.lastSavedWindowsError())
    try:
        while True:
            pCertCtx = CertEnumCertificatesInStore(hStore, pCertCtx)
            if not pCertCtx:
                break
            w_cert = space.newbytes(
                rffi.charpsize2str(pCertCtx.c_pbCertEncoded,
                                   intmask(pCertCtx.c_cbCertEncoded)))
            w_enc = w_certEncodingType(space, pCertCtx.c_dwCertEncodingType)
            w_keyusage = w_parseKeyUsage(
                space, pCertCtx, CERT_FIND_PROP_ONLY_ENHKEY_USAGE_FLAG)
            if space.is_w(w_keyusage, space.w_True):
                w_keyusage = w_parseKeyUsage(
                    space, pCertCtx, CERT_FIND_EXT_ONLY_ENHKEY_USAGE_FLAG)
            result_w.append(space.newtuple([w_cert, w_enc, w_keyusage]))
    except:
        raise
    finally:
        if pCertCtx:
            # loop ended with an error, need to clean up context manually
            CertFreeCertificateContext(pCertCtx)
        if not CertCloseStore(hStore, 0):
            # This error case might shadow another exception.
            raise wrap_windowserror(space, rwin32.lastSavedWindowsError())

    return space.newlist(result_w)

@unwrap_spec(store_name='text')
def enum_crls_w(space, store_name):
    """enum_crls(store_name) -> []

    Retrieve CRLs from Windows' cert store. store_name may be one of
    'CA', 'ROOT' or 'MY'. The system may provide more cert storages, too.
    The function returns a list of (bytes, encoding_type) tuples. The
    encoding_type flag can be interpreted with X509_ASN_ENCODING or
    PKCS_7_ASN_ENCODING."""
    result_w = []

    pCrlCtx = lltype.nullptr(CRL_CONTEXT)
    hStore = CertOpenSystemStore(None, store_name)
    if not hStore:
        raise wrap_windowserror(space, rwin32.lastSavedWindowsError())
    try:
        while True:
            pCrlCtx = CertEnumCRLsInStore(hStore, pCrlCtx)
            if not pCrlCtx:
                break
            w_crl = space.newbytes(
                rffi.charpsize2str(pCrlCtx.c_pbCrlEncoded,
                                   intmask(pCrlCtx.c_cbCrlEncoded)))
            w_enc = w_certEncodingType(space, pCrlCtx.c_dwCertEncodingType)
            result_w.append(space.newtuple([w_crl, w_enc]))
    except:
        raise
    finally:
        if pCrlCtx:
            # loop ended with an error, need to clean up context manually
            CertFreeCRLContext(pCrlCtx)
        if not CertCloseStore(hStore, 0):
            # This error case might shadow another exception.
            raise wrap_windowserror(space, rwin32.lastSavedWindowsError())

    return space.newlist(result_w)
