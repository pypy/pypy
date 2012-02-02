
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

from pypy.rlib.jit import JitDriver
from pypy.module.micronumpy import signature

def get_printable_location(shapelen, sig):
    return 'numpy ' + sig.debug_repr() + ' [%d dims]' % (shapelen,)

numpy_driver = JitDriver(
    greens=['shapelen', 'sig'],
    virtualizables=['frame'],
    reds=['frame', 'arr'],
    get_printable_location=signature.new_printable_location('numpy'),
    name='numpy',
)

def compute(arr):
    sig = arr.find_sig()
    shapelen = len(arr.shape)
    frame = sig.create_frame(arr)
    while not frame.done():
        numpy_driver.jit_merge_point(sig=sig,
                                     shapelen=shapelen,
                                     frame=frame, arr=arr)
        sig.eval(frame, arr)
        frame.next(shapelen)

