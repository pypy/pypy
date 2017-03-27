#
# A convenient read-write buffer.  Located here for want of a better place.
#

from pypy.interpreter.buffer import SimpleBuffer, ByteBuffer
from pypy.interpreter.gateway import unwrap_spec

@unwrap_spec(length=int)
def bytebuffer(space, length):
    return space.newbuffer(SimpleBuffer(ByteBuffer(length)))
