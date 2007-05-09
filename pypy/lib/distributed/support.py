
""" Some random support functions
"""

def get_remote_view(protocol):
    # this is dynamic to provide needed level of laziness
    class RemoteView(object):
        pass

    for key in protocol.remote_keys():
        getter = lambda self: protocol.get_remote(key)
        setattr(RemoteView, key, property(getter))

    return RemoteView()
