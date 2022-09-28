
/*
   DO NOT EDIT THIS FILE!

   This file is automatically generated by hpy.tools.autogen.hpyslot.autogen_hpyslot_h
   See also hpy.tools.autogen and hpy/tools/public_api.h

   Run this to regenerate:
       make autogen

*/

typedef enum {
    HPy_bf_getbuffer = 1,
    HPy_bf_releasebuffer = 2,
    HPy_mp_ass_subscript = 3,
    HPy_mp_length = 4,
    HPy_mp_subscript = 5,
    HPy_nb_absolute = 6,
    HPy_nb_add = 7,
    HPy_nb_and = 8,
    HPy_nb_bool = 9,
    HPy_nb_divmod = 10,
    HPy_nb_float = 11,
    HPy_nb_floor_divide = 12,
    HPy_nb_index = 13,
    HPy_nb_inplace_add = 14,
    HPy_nb_inplace_and = 15,
    HPy_nb_inplace_floor_divide = 16,
    HPy_nb_inplace_lshift = 17,
    HPy_nb_inplace_multiply = 18,
    HPy_nb_inplace_or = 19,
    HPy_nb_inplace_power = 20,
    HPy_nb_inplace_remainder = 21,
    HPy_nb_inplace_rshift = 22,
    HPy_nb_inplace_subtract = 23,
    HPy_nb_inplace_true_divide = 24,
    HPy_nb_inplace_xor = 25,
    HPy_nb_int = 26,
    HPy_nb_invert = 27,
    HPy_nb_lshift = 28,
    HPy_nb_multiply = 29,
    HPy_nb_negative = 30,
    HPy_nb_or = 31,
    HPy_nb_positive = 32,
    HPy_nb_power = 33,
    HPy_nb_remainder = 34,
    HPy_nb_rshift = 35,
    HPy_nb_subtract = 36,
    HPy_nb_true_divide = 37,
    HPy_nb_xor = 38,
    HPy_sq_ass_item = 39,
    HPy_sq_concat = 40,
    HPy_sq_contains = 41,
    HPy_sq_inplace_concat = 42,
    HPy_sq_inplace_repeat = 43,
    HPy_sq_item = 44,
    HPy_sq_length = 45,
    HPy_sq_repeat = 46,
    HPy_tp_init = 60,
    HPy_tp_new = 65,
    HPy_tp_repr = 66,
    HPy_tp_richcompare = 67,
    HPy_tp_traverse = 71,
    HPy_nb_matrix_multiply = 75,
    HPy_nb_inplace_matrix_multiply = 76,
    HPy_tp_finalize = 80,
    HPy_tp_destroy = 1000,
} HPySlot_Slot;

#define _HPySlot_SIG__HPy_bf_getbuffer HPyFunc_GETBUFFERPROC
#define _HPySlot_SIG__HPy_bf_releasebuffer HPyFunc_RELEASEBUFFERPROC
#define _HPySlot_SIG__HPy_mp_ass_subscript HPyFunc_OBJOBJARGPROC
#define _HPySlot_SIG__HPy_mp_length HPyFunc_LENFUNC
#define _HPySlot_SIG__HPy_mp_subscript HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_absolute HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_add HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_and HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_bool HPyFunc_INQUIRY
#define _HPySlot_SIG__HPy_nb_divmod HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_float HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_floor_divide HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_index HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_add HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_and HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_floor_divide HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_lshift HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_multiply HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_or HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_power HPyFunc_TERNARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_remainder HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_rshift HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_subtract HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_true_divide HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_xor HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_int HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_invert HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_lshift HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_multiply HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_negative HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_or HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_positive HPyFunc_UNARYFUNC
#define _HPySlot_SIG__HPy_nb_power HPyFunc_TERNARYFUNC
#define _HPySlot_SIG__HPy_nb_remainder HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_rshift HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_subtract HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_true_divide HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_xor HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_sq_ass_item HPyFunc_SSIZEOBJARGPROC
#define _HPySlot_SIG__HPy_sq_concat HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_sq_contains HPyFunc_OBJOBJPROC
#define _HPySlot_SIG__HPy_sq_inplace_concat HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_sq_inplace_repeat HPyFunc_SSIZEARGFUNC
#define _HPySlot_SIG__HPy_sq_item HPyFunc_SSIZEARGFUNC
#define _HPySlot_SIG__HPy_sq_length HPyFunc_LENFUNC
#define _HPySlot_SIG__HPy_sq_repeat HPyFunc_SSIZEARGFUNC
#define _HPySlot_SIG__HPy_tp_init HPyFunc_INITPROC
#define _HPySlot_SIG__HPy_tp_new HPyFunc_KEYWORDS
#define _HPySlot_SIG__HPy_tp_repr HPyFunc_REPRFUNC
#define _HPySlot_SIG__HPy_tp_richcompare HPyFunc_RICHCMPFUNC
#define _HPySlot_SIG__HPy_tp_traverse HPyFunc_TRAVERSEPROC
#define _HPySlot_SIG__HPy_nb_matrix_multiply HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_nb_inplace_matrix_multiply HPyFunc_BINARYFUNC
#define _HPySlot_SIG__HPy_tp_finalize HPyFunc_DESTRUCTOR
#define _HPySlot_SIG__HPy_tp_destroy HPyFunc_DESTROYFUNC
