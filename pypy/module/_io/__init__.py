from pypy.interpreter.mixedmodule import MixedModule
import sys

class Module(MixedModule):

    appleveldefs = {
        }

    interpleveldefs = {
        'DEFAULT_BUFFER_SIZE': 'space.wrap(interp_iobase.DEFAULT_BUFFER_SIZE)',
        'BlockingIOError': 'interp_io.W_BlockingIOError',
        '_IOBase': 'interp_iobase.W_IOBase',
        '_RawIOBase': 'interp_iobase.W_RawIOBase',
        '_BufferedIOBase': 'interp_bufferedio.W_BufferedIOBase',
        '_TextIOBase': 'interp_textio.W_TextIOBase',

        'FileIO': 'interp_fileio.W_FileIO',
        'BytesIO': 'interp_bytesio.W_BytesIO',
        'StringIO': 'interp_stringio.W_StringIO',
        'BufferedReader': 'interp_bufferedio.W_BufferedReader',
        'BufferedWriter': 'interp_bufferedio.W_BufferedWriter',
        'BufferedRWPair': 'interp_bufferedio.W_BufferedRWPair',
        'BufferedRandom': 'interp_bufferedio.W_BufferedRandom',
        'TextIOWrapper': 'interp_textio.W_TextIOWrapper',

        'open': 'interp_io.open',
        'IncrementalNewlineDecoder': 'interp_textio.W_IncrementalNewlineDecoder',
        }

    def init(self, space):
        w_UnsupportedOperation = space.call_function(
            space.w_type,
            space.wrap('UnsupportedOperation'),
            space.newtuple([space.w_ValueError, space.w_IOError]),
            space.newdict())
        space.setattr(self, space.wrap('UnsupportedOperation'),
                      w_UnsupportedOperation)
