
""" Some random support functions
"""

from distributed.protocol import ObjectNotFound

class RemoteView(object):
    def __init__(self, protocol):
        self.__dict__['__protocol'] = protocol

    def __getattr__(self, name):
        if name == '__dict__':
            return super(RemoteView, self).__getattr__(name)
        try:
            return self.__dict__['__protocol'].get_remote(name)
        except ObjectNotFound:
            raise AttributeError(name)
