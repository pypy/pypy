# -*- coding: iso-8859-1 -*-
""" Python 'escape' Codec


Written by Martin v. Löwis (martin@v.loewis.de).

"""
import codecs

class Codec(codecs.Codec):

    encode = staticmethod(codecs.escape_encode)
    decode = staticmethod(codecs.escape_decode)

class StreamWriter(Codec,codecs.StreamWriter):
    pass

class StreamReader(Codec,codecs.StreamReader):
    pass

def getregentry():

    return (Codec.encode,Codec.decode,StreamReader,StreamWriter)
