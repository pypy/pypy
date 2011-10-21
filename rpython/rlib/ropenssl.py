import sys

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython.translator.platform import platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib._rsocket_rffi import MAX_FD_SIZE


if sys.platform == 'win32' and platform.name != 'mingw32':
    libraries = ['libeay32', 'ssleay32', 'zlib',
                 'user32', 'advapi32', 'gdi32', 'msvcrt', 'ws2_32']
    includes = [
        # ssl.h includes winsock.h, which will conflict with our own
        # need of winsock2.  Remove this when separate compilation is
        # available...
        'winsock2.h',
        # wincrypt.h defines X509_NAME, include it here
        # so that openssl/ssl.h can repair this nonsense.
        'wincrypt.h']
else:
    libraries = ['z', 'ssl', 'crypto']
    includes = []

includes += [
    'openssl/ssl.h',
    'openssl/err.h',
    'openssl/rand.h',
    'openssl/evp.h',
    'openssl/ossl_typ.h',
    'openssl/x509v3.h']

eci = ExternalCompilationInfo(
    libraries = libraries,
    includes = includes,
    post_include_bits = [
        # Unnamed structures are not supported by rffi_platform.
        # So we replace an attribute access with a macro call.
        '#define pypy_GENERAL_NAME_dirn(name) (name->d.dirn)',
    ],
)

eci = rffi_platform.configure_external_library(
    'openssl', eci,
    [dict(prefix='openssl-',
          include_dir='inc32', library_dir='out32'),
     ])

ASN1_STRING = lltype.Ptr(lltype.ForwardReference())
ASN1_ITEM = rffi.COpaquePtr('ASN1_ITEM')
X509_NAME = rffi.COpaquePtr('X509_NAME')

class CConfigBootstrap:
    _compilation_info_ = eci
    OPENSSL_EXPORT_VAR_AS_FUNCTION = rffi_platform.Defined(
            "OPENSSL_EXPORT_VAR_AS_FUNCTION")
if rffi_platform.configure(CConfigBootstrap)["OPENSSL_EXPORT_VAR_AS_FUNCTION"]:
    ASN1_ITEM_EXP = lltype.Ptr(lltype.FuncType([], ASN1_ITEM))
else:
    ASN1_ITEM_EXP = ASN1_ITEM

class CConfig:
    _compilation_info_ = eci

    OPENSSL_VERSION_NUMBER = rffi_platform.ConstantInteger(
        "OPENSSL_VERSION_NUMBER")
    SSLEAY_VERSION = rffi_platform.DefinedConstantString(
        "SSLEAY_VERSION", "SSLeay_version(SSLEAY_VERSION)")
    OPENSSL_NO_SSL2 = rffi_platform.Defined("OPENSSL_NO_SSL2")
    OPENSSL_NO_SSL3 = rffi_platform.Defined("OPENSSL_NO_SSL3")
    SSL_FILETYPE_PEM = rffi_platform.ConstantInteger("SSL_FILETYPE_PEM")
    SSL_OP_ALL = rffi_platform.ConstantInteger("SSL_OP_ALL")
    SSL_OP_NO_SSLv2 = rffi_platform.ConstantInteger("SSL_OP_NO_SSLv2")
    SSL_OP_NO_SSLv3 = rffi_platform.ConstantInteger("SSL_OP_NO_SSLv3")
    SSL_OP_NO_TLSv1 = rffi_platform.ConstantInteger("SSL_OP_NO_TLSv1")
    SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS = rffi_platform.ConstantInteger(
        "SSL_OP_DONT_INSERT_EMPTY_FRAGMENTS")
    HAS_SNI = rffi_platform.Defined("SSL_CTRL_SET_TLSEXT_HOSTNAME")
    SSL_VERIFY_NONE = rffi_platform.ConstantInteger("SSL_VERIFY_NONE")
    SSL_VERIFY_PEER = rffi_platform.ConstantInteger("SSL_VERIFY_PEER")
    SSL_VERIFY_FAIL_IF_NO_PEER_CERT = rffi_platform.ConstantInteger("SSL_VERIFY_FAIL_IF_NO_PEER_CERT")
    SSL_ERROR_WANT_READ = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_READ")
    SSL_ERROR_WANT_WRITE = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_WRITE")
    SSL_ERROR_ZERO_RETURN = rffi_platform.ConstantInteger(
        "SSL_ERROR_ZERO_RETURN")
    SSL_ERROR_WANT_X509_LOOKUP = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_X509_LOOKUP")
    SSL_ERROR_WANT_CONNECT = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_CONNECT")
    SSL_ERROR_SYSCALL = rffi_platform.ConstantInteger("SSL_ERROR_SYSCALL")
    SSL_ERROR_SSL = rffi_platform.ConstantInteger("SSL_ERROR_SSL")
    SSL_RECEIVED_SHUTDOWN = rffi_platform.ConstantInteger(
        "SSL_RECEIVED_SHUTDOWN")
    SSL_MODE_AUTO_RETRY = rffi_platform.ConstantInteger("SSL_MODE_AUTO_RETRY")
    SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER = rffi_platform.ConstantInteger("SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER")

    NID_subject_alt_name = rffi_platform.ConstantInteger("NID_subject_alt_name")
    GEN_DIRNAME = rffi_platform.ConstantInteger("GEN_DIRNAME")
    GEN_EMAIL = rffi_platform.ConstantInteger("GEN_EMAIL")
    GEN_DNS = rffi_platform.ConstantInteger("GEN_DNS")
    GEN_URI = rffi_platform.ConstantInteger("GEN_URI")
    GEN_OTHERNAME = rffi_platform.ConstantInteger("GEN_OTHERNAME")
    GEN_X400 = rffi_platform.ConstantInteger("GEN_X400")
    GEN_EDIPARTY = rffi_platform.ConstantInteger("GEN_EDIPARTY")
    GEN_IPADD = rffi_platform.ConstantInteger("GEN_IPADD")
    GEN_RID = rffi_platform.ConstantInteger("GEN_RID")

    CRYPTO_LOCK = rffi_platform.ConstantInteger("CRYPTO_LOCK")

    OBJ_NAME_TYPE_MD_METH = rffi_platform.ConstantInteger(
        "OBJ_NAME_TYPE_MD_METH")

    # Some structures, with only the fields used in the _ssl module
    X509_name_entry_st = rffi_platform.Struct('struct X509_name_entry_st',
                                              [('set', rffi.INT)])
    asn1_string_st = rffi_platform.Struct('struct asn1_string_st',
                                          [('length', rffi.INT),
                                           ('data', rffi.CCHARP)])
    X509_extension_st = rffi_platform.Struct(
        'struct X509_extension_st',
        [('value', ASN1_STRING)])
    X509V3_EXT_D2I = lltype.FuncType([rffi.VOIDP, rffi.CCHARPP, rffi.LONG],
                                     rffi.VOIDP)
    v3_ext_method = rffi_platform.Struct(
        'struct v3_ext_method',
        [('it', ASN1_ITEM_EXP),
         ('d2i', lltype.Ptr(X509V3_EXT_D2I))])
    GENERAL_NAME_st = rffi_platform.Struct(
        'struct GENERAL_NAME_st',
        [('type', rffi.INT)])
    EVP_MD_st = rffi_platform.Struct(
        'EVP_MD',
        [('md_size', rffi.INT),
         ('block_size', rffi.INT)])
    EVP_MD_SIZE = rffi_platform.SizeOf('EVP_MD')
    EVP_MD_CTX_SIZE = rffi_platform.SizeOf('EVP_MD_CTX')

    OBJ_NAME_st = rffi_platform.Struct(
        'OBJ_NAME',
        [('alias', rffi.INT),
         ('name', rffi.CCHARP),
         ])

    OBJ_NAME_st = rffi_platform.Struct(
        'OBJ_NAME',
        [('alias', rffi.INT),
         ('name', rffi.CCHARP),
         ])


for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

# opaque structures
SSL_METHOD = rffi.COpaquePtr('SSL_METHOD')
SSL_CTX = rffi.COpaquePtr('SSL_CTX')
SSL_CIPHER = rffi.COpaquePtr('SSL_CIPHER')
SSL = rffi.COpaquePtr('SSL')
BIO = rffi.COpaquePtr('BIO')
X509 = rffi.COpaquePtr('X509')
X509_NAME_ENTRY = rffi.CArrayPtr(X509_name_entry_st)
X509_EXTENSION = rffi.CArrayPtr(X509_extension_st)
X509V3_EXT_METHOD = rffi.CArrayPtr(v3_ext_method)
ASN1_OBJECT = rffi.COpaquePtr('ASN1_OBJECT')
ASN1_STRING.TO.become(asn1_string_st)
ASN1_TIME = rffi.COpaquePtr('ASN1_TIME')
ASN1_INTEGER = rffi.COpaquePtr('ASN1_INTEGER')
GENERAL_NAMES = rffi.COpaquePtr('GENERAL_NAMES')
GENERAL_NAME = rffi.CArrayPtr(GENERAL_NAME_st)
OBJ_NAME = rffi.CArrayPtr(OBJ_NAME_st)

HAVE_OPENSSL_RAND = OPENSSL_VERSION_NUMBER >= 0x0090500f
HAVE_SSL_CTX_CLEAR_OPTIONS = OPENSSL_VERSION_NUMBER >= 0x009080df

def external(name, argtypes, restype, **kw):
    kw['compilation_info'] = eci
    return rffi.llexternal(
        name, argtypes, restype, **kw)

def ssl_external(name, argtypes, restype, **kw):
    globals()['libssl_' + name] = external(
        name, argtypes, restype, **kw)

ssl_external('SSL_load_error_strings', [], lltype.Void)
ssl_external('SSL_library_init', [], rffi.INT)
ssl_external('CRYPTO_num_locks', [], rffi.INT)
ssl_external('CRYPTO_set_locking_callback',
             [lltype.Ptr(lltype.FuncType(
                [rffi.INT, rffi.INT, rffi.CCHARP, rffi.INT], lltype.Void))],
             lltype.Void)
ssl_external('CRYPTO_set_id_callback',
             [lltype.Ptr(lltype.FuncType([], rffi.LONG))],
             lltype.Void)

if HAVE_OPENSSL_RAND:
    ssl_external('RAND_add', [rffi.CCHARP, rffi.INT, rffi.DOUBLE], lltype.Void)
    ssl_external('RAND_status', [], rffi.INT)
    ssl_external('RAND_egd', [rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_new', [SSL_METHOD], SSL_CTX)
ssl_external('SSL_get_SSL_CTX', [SSL], SSL_CTX)
ssl_external('TLSv1_method', [], SSL_METHOD)
ssl_external('SSLv2_method', [], SSL_METHOD)
ssl_external('SSLv3_method', [], SSL_METHOD)
ssl_external('SSLv23_method', [], SSL_METHOD)
ssl_external('SSL_CTX_use_PrivateKey_file', [SSL_CTX, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_CTX_use_certificate_chain_file', [SSL_CTX, rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_get_options', [SSL_CTX], rffi.LONG, macro=True)
ssl_external('SSL_CTX_set_options', [SSL_CTX, rffi.LONG], rffi.LONG, macro=True)
if HAVE_SSL_CTX_CLEAR_OPTIONS:
    ssl_external('SSL_CTX_clear_options', [SSL_CTX, rffi.LONG], rffi.LONG,
                 macro=True)
ssl_external('SSL_CTX_ctrl', [SSL_CTX, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_CTX_set_verify', [SSL_CTX, rffi.INT, rffi.VOIDP], lltype.Void)
ssl_external('SSL_CTX_get_verify_mode', [SSL_CTX], rffi.INT)
ssl_external('SSL_CTX_set_default_verify_paths', [SSL_CTX], rffi.INT)
ssl_external('SSL_CTX_set_cipher_list', [SSL_CTX, rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_load_verify_locations', [SSL_CTX, rffi.CCHARP, rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_check_private_key', [SSL_CTX], rffi.INT)
ssl_external('SSL_CTX_set_session_id_context', [SSL_CTX, rffi.CCHARP, rffi.UINT], rffi.INT)
SSL_CTX_STATS_NAMES = """
    number connect connect_good connect_renegotiate accept accept_good
    accept_renegotiate hits misses timeouts cache_full""".split()
SSL_CTX_STATS = unrolling_iterable(
    (name, external('SSL_CTX_sess_' + name, [SSL_CTX], rffi.LONG, macro=True))
    for name in SSL_CTX_STATS_NAMES)

ssl_external('SSL_new', [SSL_CTX], SSL)
ssl_external('SSL_set_fd', [SSL, rffi.INT], rffi.INT)
ssl_external('SSL_set_mode', [SSL, rffi.INT], rffi.INT, macro=True)
ssl_external('SSL_ctrl', [SSL, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('BIO_ctrl', [BIO, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_get_rbio', [SSL], BIO)
ssl_external('SSL_get_wbio', [SSL], BIO)
ssl_external('SSL_set_connect_state', [SSL], lltype.Void)
ssl_external('SSL_set_accept_state', [SSL], lltype.Void)
ssl_external('SSL_connect', [SSL], rffi.INT)
ssl_external('SSL_do_handshake', [SSL], rffi.INT)
ssl_external('SSL_shutdown', [SSL], rffi.INT)
ssl_external('SSL_get_error', [SSL, rffi.INT], rffi.INT)
ssl_external('SSL_get_shutdown', [SSL], rffi.INT)
ssl_external('SSL_set_read_ahead', [SSL, rffi.INT], lltype.Void)
ssl_external('SSL_set_tlsext_host_name', [SSL, rffi.CCHARP], rffi.INT, macro=True)

ssl_external('SSL_get_peer_certificate', [SSL], X509)
ssl_external('X509_get_subject_name', [X509], X509_NAME)
ssl_external('X509_get_issuer_name', [X509], X509_NAME)
ssl_external('X509_NAME_oneline', [X509_NAME, rffi.CCHARP, rffi.INT], rffi.CCHARP)
ssl_external('X509_NAME_entry_count', [X509_NAME], rffi.INT)
ssl_external('X509_NAME_get_entry', [X509_NAME, rffi.INT], X509_NAME_ENTRY)
ssl_external('X509_NAME_ENTRY_get_object', [X509_NAME_ENTRY], ASN1_OBJECT)
ssl_external('X509_NAME_ENTRY_get_data', [X509_NAME_ENTRY], ASN1_STRING)
ssl_external('i2d_X509', [X509, rffi.CCHARPP], rffi.INT)
ssl_external('X509_free', [X509], lltype.Void, releasegil=False)
ssl_external('X509_get_notBefore', [X509], ASN1_TIME, macro=True)
ssl_external('X509_get_notAfter', [X509], ASN1_TIME, macro=True)
ssl_external('X509_get_serialNumber', [X509], ASN1_INTEGER)
ssl_external('X509_get_version', [X509], rffi.INT, macro=True)
ssl_external('X509_get_ext_by_NID', [X509, rffi.INT, rffi.INT], rffi.INT)
ssl_external('X509_get_ext', [X509, rffi.INT], X509_EXTENSION)
ssl_external('X509V3_EXT_get', [X509_EXTENSION], X509V3_EXT_METHOD)


ssl_external('OBJ_obj2txt',
             [rffi.CCHARP, rffi.INT, ASN1_OBJECT, rffi.INT], rffi.INT)
ssl_external('ASN1_STRING_data', [ASN1_STRING], rffi.CCHARP)
ssl_external('ASN1_STRING_length', [ASN1_STRING], rffi.INT)
ssl_external('ASN1_STRING_to_UTF8', [rffi.CCHARPP, ASN1_STRING], rffi.INT)
ssl_external('ASN1_TIME_print', [BIO, ASN1_TIME], rffi.INT)
ssl_external('i2a_ASN1_INTEGER', [BIO, ASN1_INTEGER], rffi.INT)
ssl_external('ASN1_item_d2i',
             [rffi.VOIDP, rffi.CCHARPP, rffi.LONG, ASN1_ITEM], rffi.VOIDP)
ssl_external('ASN1_ITEM_ptr', [ASN1_ITEM_EXP], ASN1_ITEM, macro=True)

ssl_external('sk_GENERAL_NAME_num', [GENERAL_NAMES], rffi.INT,
             macro=True)
ssl_external('sk_GENERAL_NAME_value', [GENERAL_NAMES, rffi.INT], GENERAL_NAME,
             macro=True)
ssl_external('GENERAL_NAME_print', [BIO, GENERAL_NAME], rffi.INT)
ssl_external('pypy_GENERAL_NAME_dirn', [GENERAL_NAME], X509_NAME,
             macro=True)

ssl_external('SSL_get_current_cipher', [SSL], SSL_CIPHER)
ssl_external('SSL_CIPHER_get_name', [SSL_CIPHER], rffi.CCHARP)
ssl_external('SSL_CIPHER_get_version', [SSL_CIPHER], rffi.CCHARP)
ssl_external('SSL_CIPHER_get_bits', [SSL_CIPHER, rffi.INTP], rffi.INT)

ssl_external('ERR_get_error', [], rffi.INT)
ssl_external('ERR_peek_last_error', [], rffi.INT)
ssl_external('ERR_error_string', [rffi.ULONG, rffi.CCHARP], rffi.CCHARP)
ssl_external('ERR_clear_error', [], lltype.Void)

# 'releasegil=False' here indicates that this function will be called
# with the GIL held, and so is allowed to run in a RPython __del__ method.
ssl_external('SSL_free', [SSL], lltype.Void, releasegil=False)
ssl_external('SSL_CTX_free', [SSL_CTX], lltype.Void, releasegil=False)
ssl_external('CRYPTO_free', [rffi.VOIDP], lltype.Void)
libssl_OPENSSL_free = libssl_CRYPTO_free

ssl_external('SSL_write', [SSL, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_pending', [SSL], rffi.INT)
ssl_external('SSL_read', [SSL, rffi.CCHARP, rffi.INT], rffi.INT)

BIO_METHOD = rffi.COpaquePtr('BIO_METHOD')
ssl_external('BIO_s_mem', [], BIO_METHOD)
ssl_external('BIO_s_file', [], BIO_METHOD)
ssl_external('BIO_new', [BIO_METHOD], BIO)
ssl_external('BIO_set_nbio', [BIO, rffi.INT], rffi.INT, macro=True)
ssl_external('BIO_free', [BIO], rffi.INT)
ssl_external('BIO_reset', [BIO], rffi.INT, macro=True)
ssl_external('BIO_read_filename', [BIO, rffi.CCHARP], rffi.INT, macro=True)
ssl_external('BIO_gets', [BIO, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('PEM_read_bio_X509_AUX',
             [BIO, rffi.VOIDP, rffi.VOIDP, rffi.VOIDP], X509)

EVP_MD_CTX = rffi.COpaquePtr('EVP_MD_CTX', compilation_info=eci)
EVP_MD     = lltype.Ptr(EVP_MD_st)

OpenSSL_add_all_digests = external(
    'OpenSSL_add_all_digests', [], lltype.Void)
EVP_get_digestbyname = external(
    'EVP_get_digestbyname',
    [rffi.CCHARP], EVP_MD)
EVP_DigestInit = external(
    'EVP_DigestInit',
    [EVP_MD_CTX, EVP_MD], rffi.INT)
EVP_DigestUpdate = external(
    'EVP_DigestUpdate',
    [EVP_MD_CTX, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
EVP_DigestFinal = external(
    'EVP_DigestFinal',
    [EVP_MD_CTX, rffi.CCHARP, rffi.VOIDP], rffi.INT)
EVP_MD_CTX_copy = external(
    'EVP_MD_CTX_copy', [EVP_MD_CTX, EVP_MD_CTX], rffi.INT)
EVP_MD_CTX_cleanup = external(
    'EVP_MD_CTX_cleanup', [EVP_MD_CTX], rffi.INT, releasegil=False)

OBJ_NAME_CALLBACK = lltype.Ptr(lltype.FuncType(
        [OBJ_NAME, rffi.VOIDP], lltype.Void))
OBJ_NAME_do_all = external(
    'OBJ_NAME_do_all', [rffi.INT, OBJ_NAME_CALLBACK, rffi.VOIDP], lltype.Void)

# HASH_MALLOC_SIZE is the size of EVP_MD, EVP_MD_CTX plus their points
# Used for adding memory pressure. Last number is an (under?)estimate of
# EVP_PKEY_CTX's size.
# XXX: Make a better estimate here
HASH_MALLOC_SIZE = EVP_MD_SIZE + EVP_MD_CTX_SIZE \
        + rffi.sizeof(EVP_MD) * 2 + 208

OBJ_NAME_CALLBACK = lltype.Ptr(lltype.FuncType(
        [OBJ_NAME, rffi.VOIDP], lltype.Void))
OBJ_NAME_do_all = external(
    'OBJ_NAME_do_all', [rffi.INT, OBJ_NAME_CALLBACK, rffi.VOIDP], lltype.Void)

def init_ssl():
    libssl_SSL_load_error_strings()
    libssl_SSL_library_init()

def init_digests():
    OpenSSL_add_all_digests()
