
try:
    from protocol import RemoteProtocol, test_env, remote_loop
except ImportError:
    # UGH. This is needed for tests
    pass
