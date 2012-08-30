
""" This file is the main run loop as well as evaluation loops for various
signatures
"""

def call2(func, name, calc_dtype, res_dtype, w_lhs, w_rhs, out):
    left_iter = w_lhs.create_iter()
    right_iter = w_rhs.create_iter()
    out_iter = out.create_iter()
    while not out_iter.done():
        w_left = left_iter.getitem().convert_to(calc_dtype)
        w_right = right_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, w_left, w_right).convert_to(
            res_dtype))
        left_iter.next()
        right_iter.next()
        out_iter.next()
    return out

def call1(func, name , calc_dtype, res_dtype, w_obj, out):
    obj_iter = w_obj.create_iter()
    out_iter = out.create_iter()
    while not out_iter.done():
        elem = obj_iter.getitem().convert_to(calc_dtype)
        out_iter.setitem(func(calc_dtype, elem).convert_to(res_dtype))
        out_iter.next()
        obj_iter.next()
    return out

# from pypy.rlib.jit import JitDriver, hint, unroll_safe, promote
# from pypy.module.micronumpy.interp_iter import ConstantIterator

# class NumpyEvalFrame(object):
#     _virtualizable2_ = ['iterators[*]', 'final_iter', 'arraylist[*]',
#                         'value', 'identity', 'cur_value']

#     @unroll_safe
#     def __init__(self, iterators, arrays):
#         self = hint(self, access_directly=True, fresh_virtualizable=True)
#         self.iterators = iterators[:]
#         self.arrays = arrays[:]
#         for i in range(len(self.iterators)):
#             iter = self.iterators[i]
#             if not isinstance(iter, ConstantIterator):
#                 self.final_iter = i
#                 break
#         else:
#             self.final_iter = -1
#         self.cur_value = None
#         self.identity = None

#     def done(self):
#         final_iter = promote(self.final_iter)
#         if final_iter < 0:
#             assert False
#         return self.iterators[final_iter].done()

#     @unroll_safe
#     def next(self, shapelen):
#         for i in range(len(self.iterators)):
#             self.iterators[i] = self.iterators[i].next(shapelen)

#     @unroll_safe
#     def next_from_second(self, shapelen):
#         """ Don't increase the first iterator
#         """
#         for i in range(1, len(self.iterators)):
#             self.iterators[i] = self.iterators[i].next(shapelen)

#     def next_first(self, shapelen):
#         self.iterators[0] = self.iterators[0].next(shapelen)

#     def get_final_iter(self):
#         final_iter = promote(self.final_iter)
#         if final_iter < 0:
#             assert False
#         return self.iterators[final_iter]

# def get_printable_location(shapelen, sig):
#     return 'numpy ' + sig.debug_repr() + ' [%d dims]' % (shapelen,)

# numpy_driver = JitDriver(
#     greens=['shapelen', 'sig'],
#     virtualizables=['frame'],
#     reds=['frame', 'arr'],
#     get_printable_location=get_printable_location,
#     name='numpy',
# )

# class ComputationDone(Exception):
#     def __init__(self, value):
#         self.value = value

# def compute(arr):
#     sig = arr.find_sig()
#     shapelen = len(arr.shape)
#     frame = sig.create_frame(arr)
#     try:
#         while not frame.done():
#             numpy_driver.jit_merge_point(sig=sig,
#                                          shapelen=shapelen,
#                                          frame=frame, arr=arr)
#             sig.eval(frame, arr)
#             frame.next(shapelen)
#         return frame.cur_value
#     except ComputationDone, e:
#         return e.value
