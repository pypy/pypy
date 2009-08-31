import os, sys, new

# WARNING: this is all nicely RPython, but there is no RPython code around
# to *compile* regular expressions, so outside of PyPy this is only useful
# for RPython applications that just need precompiled regexps.
#
# XXX However it's not even clear how to get such prebuilt regexps...

import rsre_core
rsre_core_filename = rsre_core.__file__
if rsre_core_filename[-1] in 'oc':
    rsre_core_filename = rsre_core_filename[:-1]
rsre_core_filename = os.path.abspath(rsre_core_filename)
del rsre_core
from pypy.rlib.rsre.rsre_char import getlower

def insert_sre_methods(locals, name):
    """A hack that inserts the SRE entry point methods into the 'locals'
    scope, which should be the __dict__ of a State class.  The State
    class defines methods to look at the input string or unicode string.
    It should provide the following API for sre_core:

        get_char_ord(p) - return the ord of the char at position 'p'
        lower(charcode) - return the ord of the lowcase version of 'charcode'
        start           - start position for searching and matching
        end             - end position for searching and matching
    """
    filename = rsre_core_filename 
    rsre_core = new.module('pypy.rlib.rsre.rsre_core_' + name)
    rsre_core.__file__ = filename
    execfile(filename, rsre_core.__dict__)
    for key, value in rsre_core.StateMixin.__dict__.items():
        if not key.startswith('__'):
            locals[key] = value
    locals['rsre_core'] = rsre_core     # for tests

def set_unicode_db(unicodedb):
    """Another hack to set the unicodedb used by rsre_char.  I guess there
    is little point in allowing several different unicodedb's in the same
    RPython program...  See comments in rsre_char.
    """
    from pypy.rlib.rsre import rsre_char
    rsre_char.unicodedb = unicodedb


class SimpleStringState(object):
    """Prebuilt state for matching strings, for testing and for
    stand-alone RPython applictions that don't worry about unicode.
    """
    insert_sre_methods(locals(), 'simple')

    def __init__(self, string, start=0, end=-1):
        self.string = string
        if end < 0:
            end = len(string)
        self.start = start
        self.end = end
        self.reset()

    def get_char_ord(self, p):
        return ord(self.string[p])

    def lower(self, char_ord):
        return getlower(char_ord, 0)
