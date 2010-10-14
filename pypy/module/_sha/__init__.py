
"""
Mixed-module definition for the sha module.
Note that there is also a pure Python implementation in pypy/lib/sha.py;
the present mixed-module version of sha takes precedence if it is enabled.
"""

from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    """\
This module implements the interface to NIST's secure hash algorithm,
known as SHA-1. SHA-1 is an improved version of the original SHA hash
algorithm. It is used in the same way as the md5 module: use new() to
create an sha object, then feed this object with arbitrary strings using
the update() method, and at any point you can ask it for the digest of
the concatenation of the strings fed to it so far. SHA-1 digests are 160
bits instead of MD5's 128 bits."""

    interpleveldefs = {
        'new': 'interp_sha.W_SHA',
        'SHAType': 'interp_sha.W_SHA',
        'blocksize': 'space.wrap(1)',
        'digest_size': 'space.wrap(20)',
        'digestsize': 'space.wrap(20)',
        }

    appleveldefs = {
        }
