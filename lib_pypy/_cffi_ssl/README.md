# PyPy's SSL module

All of the CFFI code is copied from cryptography. PyPy vendors it's own copy of
the cffi backend thus it renames the compiled shared object to _pypy_openssl.so
(which means that cryptography can ship their own cffi backend)

# Modifications to cryptography 2.7

- `_cffi_src/openssl/asn1.py` : revert removal of `ASN1_TIME_print`,
  `ASN1_ITEM`, `ASN1_ITEM_EXP`, `ASN1_VALUE`, `ASN1_item_d2i`
- `_cffi_src/openssl/bio.py` : revert removal of `BIO_s_file`, `BIO_read_filename`
- `_cffi_src/openssl/evp.py` : revert removal of `EVP_MD_size`
- `_cffi_src/openssl/nid.py` : revert removal of `NID_ad_OCSP`,
  `NID_info_access`, `NID_ad_ca_issuers`, `NID_crl_distribution_points`
- `_cffi_src/openssl/pem.py` : revert removal of `PEM_read_bio_X509_AUX`
- `_cffi_src/openssl/x509.py` : revert removal of `X509_get_ext_by_NID`,
  `i2d_X509`
- `_cffi_src/openssl/x509v3.py` : revert removal of `X509V3_EXT_get`,
  `X509V3_EXT_METHOD`
- `_cffi_src/openssl/ssl.py: expose Cryptography_HAS_CTRL_GET_MAX_PROTO_VERSION

# Tests?

Currently this module is tested using CPython's standard library test suite.

# Install it into PyPy's source tree

Copy over all the sources into the folder `lib_pypy/_cffi_ssl/*`. Updating the cffi backend can be simply done by the following command::

    $ cp -r <cloned cryptography folder>/src/* .

# Crpytography version

Copied over release version `2.7`
