import sys

if sys.platform != 'win32':
    from py.test import skip
    skip("ssl.enum_certificates is only available on Windows")

class AppTestWin32:
    spaceconfig = dict(usemodules=('_ssl',))

    def setup_class(cls):
        if sys.platform != 'win32':
            py.test.skip("pexpect not found")

    def test_enum_certificates(self):
        import _ssl
        assert _ssl.enum_certificates("CA")
        assert _ssl.enum_certificates("ROOT")

        raises(TypeError, _ssl.enum_certificates)
        raises(WindowsError, _ssl.enum_certificates, "")

        trust_oids = set()
        for storename in ("CA", "ROOT"):
            store = _ssl.enum_certificates(storename)
            assert isinstance(store, list)
            for element in store:
                assert isinstance(element, tuple)
                assert len(element) == 3
                cert, enc, trust = element
                assert isinstance(cert, bytes)
                assert enc in {"x509_asn", "pkcs_7_asn"}
                assert isinstance(trust, (set, bool))
                if isinstance(trust, set):
                    trust_oids.update(trust)

        serverAuth = "1.3.6.1.5.5.7.3.1"
        assert serverAuth in trust_oids

    def test_enum_crls(self):
        import _ssl
        assert _ssl.enum_crls("CA")
        raises(TypeError, _ssl.enum_crls)
        raises(WindowsError, _ssl.enum_crls, "")

        crls = _ssl.enum_crls("CA")
        assert isinstance(crls, list)
        for element in crls:
            assert isinstance(element, tuple)
            assert len(element) == 2
            assert isinstance(element[0], bytes)
            assert element[1] in {"x509_asn", "pkcs_7_asn"}


