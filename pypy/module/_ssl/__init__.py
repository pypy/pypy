import sys
from rpython.rlib.rarithmetic import intmask
from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._ssl import ssl_data

class Module(MixedModule):
    """Implementation module for SSL socket operations.
    See the socket module for documentation."""

    interpleveldefs = {
        '_test_decode_cert': 'interp_ssl._test_decode_cert',
        'txt2obj': 'interp_ssl.txt2obj',
        'nid2obj': 'interp_ssl.nid2obj',
        'get_default_verify_paths': 'interp_ssl.get_default_verify_paths',

        'SSLError': 'interp_ssl.get_error(space).w_error',
        'SSLZeroReturnError': 'interp_ssl.get_error(space).w_ZeroReturnError',
        'SSLWantReadError': 'interp_ssl.get_error(space).w_WantReadError',
        'SSLWantWriteError': 'interp_ssl.get_error(space).w_WantWriteError',
        'SSLEOFError': 'interp_ssl.get_error(space).w_EOFError',
        'SSLSyscallError': 'interp_ssl.get_error(space).w_SyscallError',

        '_SSLSocket': 'interp_ssl.SSLSocket',
        '_SSLContext': 'interp_ssl.SSLContext',
        'MemoryBIO': 'interp_ssl.MemoryBIO',
    }

    if sys.platform == 'win32':
        interpleveldefs['enum_certificates'] = 'interp_win32.enum_certificates_w'
        interpleveldefs['enum_crls'] = 'interp_win32.enum_crls_w'

    appleveldefs = {
    }

    @classmethod
    def buildloaders(cls):
        # init the SSL module
        from pypy.module._ssl.interp_ssl import constants, HAVE_OPENSSL_RAND

        for constant, value in constants.iteritems():
            if constant.startswith('OP_'):
                value = intmask(value)  # Convert to C long and wrap around.
            Module.interpleveldefs[constant] = "space.wrap(%r)" % (value,)

        if HAVE_OPENSSL_RAND:
            Module.interpleveldefs['RAND_add'] = "interp_ssl.RAND_add"
            Module.interpleveldefs['RAND_bytes'] = "interp_ssl.RAND_bytes"
            Module.interpleveldefs['RAND_pseudo_bytes'] = "interp_ssl.RAND_pseudo_bytes"
            Module.interpleveldefs['RAND_status'] = "interp_ssl.RAND_status"
            Module.interpleveldefs['RAND_egd'] = "interp_ssl.RAND_egd"

        for name, value in ssl_data.ALERT_DESCRIPTION_CODES.items():
            Module.interpleveldefs[name] = "space.wrap(%r)" % value

        super(Module, cls).buildloaders()

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        from pypy.module._ssl.interp_ssl import PWINFO_STORAGE
        PWINFO_STORAGE.clear()

    def startup(self, space):
        from rpython.rlib.ropenssl import init_ssl
        init_ssl()
        if space.config.objspace.usemodules.thread:
            from pypy.module._ssl.thread_lock import setup_ssl_threads
            setup_ssl_threads()
