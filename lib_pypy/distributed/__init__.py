
try:
    from protocol import RemoteProtocol, test_env, remote_loop, ObjectNotFound
except ImportError:
    # XXX fix it
    # UGH. This is needed for tests
    pass
