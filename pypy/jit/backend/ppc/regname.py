class _R(int):
    def __repr__(self):
        return "r%s"%(super(_R, self).__repr__(),)
    __str__ = __repr__
class _F(int):
    def __repr__(self):
        return "fr%s"%(super(_F, self).__repr__(),)
    __str__ = __repr__

r0, r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, \
    r13, r14, r15, r16, r17, r18, r19, r20, r21, r22, \
    r23, r24, r25, r26, r27, r28, r29, r30, r31 = map(_R, range(32))

fr0, fr1, fr2, fr3, fr4, fr5, fr6, fr7, fr8, fr9, fr10, fr11, fr12, \
     fr13, fr14, fr15, fr16, fr17, fr18, fr19, fr20, fr21, fr22, \
     fr23, fr24, fr25, fr26, fr27, fr28, fr29, fr30, fr31 = map(_F, range(32))

crf0, crf1, crf2, crf3, crf4, crf5, crf6, crf7 = range(8)
