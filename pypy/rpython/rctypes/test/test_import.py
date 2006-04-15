"""
Checks that importing and registering the annotations for rctypes
doesn't bring in the whole rtyper.
"""

import py, sys

def test_import():
    gw = py.execnet.PopenGateway()
    channel = gw.remote_exec('''
        import sys
        sys.path = channel.receive()
        import pypy.rpython.rctypes.implementation
        channel.send(sys.modules.keys())
    ''')
    channel.send(sys.path)
    modules = channel.receive()
    assert 'pypy.rpython.rmodel' not in modules
