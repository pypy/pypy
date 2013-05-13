"""Support for OpenBSD."""

import os

from rpython.translator.platform.bsd import BSD

class OpenBSD(BSD):
    DEFAULT_CC = "cc"
    name = "openbsd"

    link_flags = os.environ.get("LDFLAGS", '-pthread').split()
    cflags = os.environ.get("CFLAGS", "-O3 -pthread -fomit-frame-pointer -D_BSD_SOURCE").split()

    def _libs(self, libraries):
        libraries=set(libraries + ("intl", "iconv", "compat"))
        return ['-l%s' % lib for lib in libraries if lib not in ["crypt", "dl", "rt"]]

class OpenBSD_64(OpenBSD):
    shared_only = ('-fPIC',)
