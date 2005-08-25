extdeclarations = """
;ll_math.py
declare ccc double %acos(double)
declare ccc double %asin(double)
declare ccc double %atan(double)
declare ccc double %ceil(double)
declare ccc double %cos(double)
declare ccc double %cosh(double)
declare ccc double %exp(double)
declare ccc double %fabs(double)
declare ccc double %floor(double)
declare ccc double %log(double)
declare ccc double %log10(double)
declare ccc double %sin(double)
declare ccc double %sinh(double)
declare ccc double %sqrt(double)
declare ccc double %tan(double)
declare ccc double %tanh(double)
declare ccc double %atan2(double,double)
declare ccc double %fmod(double,double)

%__ll_math_frexp = internal constant [12 x sbyte] c"frexp......\\00"
%__ll_math_hypot = internal constant [12 x sbyte] c"hypot......\\00"
%__ll_math_ldexp = internal constant [12 x sbyte] c"ldexp......\\00"
%__ll_math_modf  = internal constant [12 x sbyte] c"modf.......\\00"
%__ll_math_pow   = internal constant [12 x sbyte] c"pow........\\00"
"""

extfunctions = {}

#functions with a one-to-one C equivalent
simple_functions = [
    ('double %x', ['acos','asin','atan','ceil','cos','cosh','exp','fabs',
                   'floor','log','log10','sin','sinh','sqrt','tan','tanh']),
    ('double %x, double %y', ['atan2','fmod']),
    ]

simple_function_template = """
internal fastcc double %%ll_math_%(function)s(%(params)s) {
    %%t = call ccc double %%%(function)s(%(params)s)
    ret double %%t
}

"""

for params, functions in simple_functions:
    for function in functions:
        extfunctions["%ll_math_" + function] = ((), simple_function_template % locals())

#extfunctions["%ll_math_frexp"] = (("%__debug",), """
#internal fastcc %RPyFREXP_RESULT* %ll_math_frexp(double %x) {
#    call fastcc void %__debug([12 x sbyte]* %__ll_math_frexp) ; XXX: TODO: ll_math_frexp
#    ret %RPyFREXP_RESULT* null
#}
#""")

extfunctions["%ll_math_hypot"] = (("%__debug",), """
internal fastcc double %ll_math_hypot(double %x, double %y) {
    call fastcc void %__debug([12 x sbyte]* %__ll_math_hypot) ; XXX: TODO: ll_math_hypot
    ret double 0.0
}
""")

extfunctions["%ll_math_ldexp"] = (("%__debug",), """
internal fastcc double %ll_math_ldexp(double %x, INT %y) {
    call fastcc void %__debug([12 x sbyte]* %__ll_math_ldexp) ; XXX: TODO: ll_math_ldexp
    ret double 0.0
}
""")

extfunctions["%ll_math_modf"] = (("%__debug",), """
internal fastcc %RPyMODF_RESULT* %ll_math_modf(double %x) {
    call fastcc void %__debug([12 x sbyte]* %__ll_math_modf) ; XXX: TODO: ll_math_modf
    ret %RPyMODF_RESULT* null
}
""")

extfunctions["%ll_math_pow"] = (("%__debug",), """
internal fastcc double %ll_math_pow(double %x, double %y) {
    call fastcc void %__debug([12 x sbyte]* %__ll_math_pow) ; XXX: TODO: ll_math_pow
    ret double 0.0
}
""")
#;;;XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


extfunctions["%ll_math_frexp"] = (("%prepare_and_raise_OverflowError",
                                   "%prepare_and_raise_ValueError"), """
declare int* %__errno_location()

internal fastcc int %ll_math_is_error(double %x) {  
entry:
	%x_addr = alloca double		 ; ty=double*
	%result = alloca int		 ; ty=int*
	store double %x, double* %x_addr
	%tmp.0 = call int* ()* %__errno_location()		 ; ty=int*
	%tmp.1 = load int* %tmp.0		 ; ty=int
	%tmp.2 = seteq int %tmp.1, 34		 ; ty=bool
	%tmp.3 = cast bool %tmp.2 to int		 ; ty=int
	br bool %tmp.2, label %then.0, label %else
then.0:
	%tmp.4 = load double* %x_addr		 ; ty=double
	%tmp.5 = seteq double %tmp.4, 0x0000000000000000		 ; ty=bool
	%tmp.6 = cast bool %tmp.5 to int		 ; ty=int
	br bool %tmp.5, label %then.1, label %endif.1
then.1:
	store int 0, int* %result
	br label %return
after_ret.0:
	br label %endif.1
endif.1:
	call fastcc void (sbyte*)* %prepare_and_raise_OverflowError(sbyte* getelementptr ([17 x sbyte]* %.str_1, int 0, int 0))
	br label %endif.0
else:
	call fastcc void (sbyte*)* %prepare_and_raise_ValueError(sbyte* getelementptr ([18 x sbyte]* %.str_2, int 0, int 0))
	br label %endif.0
endif.0:
	store int 1, int* %result
	br label %return
after_ret.1:
	br label %return
return:
	%tmp.9 = load int* %result		 ; ty=int
	ret int %tmp.9
}

internal fastcc %RPyFREXP_RESULT* %ll_math_frexp(double %x) {  
entry:
	%x_addr = alloca double		 ; ty=double*
	%result = alloca %RPyFREXP_RESULT*		 ; ty=%RPyFREXP_RESULT**
	%expo = alloca int		 ; ty=int*
	%m = alloca double		 ; ty=double*
	store double %x, double* %x_addr
	%tmp.0 = call int* ()* %__errno_location()		 ; ty=int*
	store int 0, int* %tmp.0
	%tmp.2 = load double* %x_addr		 ; ty=double
	%tmp.1 = call double (double, int*)* %frexp(double %tmp.2, int* %expo)		 ; ty=double
	store double %tmp.1, double* %m
	%tmp.3 = call int* ()* %__errno_location()		 ; ty=int*
	%tmp.4 = load int* %tmp.3		 ; ty=int
	%tmp.5 = seteq int %tmp.4, 0		 ; ty=bool
	%tmp.6 = cast bool %tmp.5 to int		 ; ty=int
	br bool %tmp.5, label %shortcirc_next.0, label %shortcirc_done.0
shortcirc_next.0:
	%tmp.7 = load double* %m		 ; ty=double
	%tmp.8 = setgt double %tmp.7, 0x7FEFFFFFFFFFFFFF		 ; ty=bool
	%tmp.9 = cast bool %tmp.8 to int		 ; ty=int
	br bool %tmp.8, label %shortcirc_done.1, label %shortcirc_next.1
shortcirc_next.1:
	%tmp.10 = load double* %m		 ; ty=double
	%tmp.11 = setlt double %tmp.10, 0xFFEFFFFFFFFFFFFF		 ; ty=bool
	%tmp.12 = cast bool %tmp.11 to int		 ; ty=int
	br label %shortcirc_done.1
shortcirc_done.1:
	%shortcirc_val.0 = phi bool [ true, %shortcirc_next.0 ], [ %tmp.11, %shortcirc_next.1 ]		 ; ty=bool
	%tmp.13 = cast bool %shortcirc_val.0 to int		 ; ty=int
	br label %shortcirc_done.0
shortcirc_done.0:
	%shortcirc_val.1 = phi bool [ false, %entry ], [ %shortcirc_val.0, %shortcirc_done.1 ]		 ; ty=bool
	%tmp.14 = cast bool %shortcirc_val.1 to int		 ; ty=int
	br bool %shortcirc_val.1, label %then.0, label %endif.0
then.0:
	%tmp.15 = call int* ()* %__errno_location()		 ; ty=int*
	store int 34, int* %tmp.15
	br label %endif.0
endif.0:
	%tmp.16 = call int* ()* %__errno_location()		 ; ty=int*
	%tmp.17 = load int* %tmp.16		 ; ty=int
	%tmp.18 = setne int %tmp.17, 0		 ; ty=bool
	%tmp.19 = cast bool %tmp.18 to int		 ; ty=int
	br bool %tmp.18, label %shortcirc_next.2, label %shortcirc_done.2
shortcirc_next.2:
	%tmp.21 = load double* %m		 ; ty=double
	%tmp.20 = call fastcc int (double)* %ll_math_is_error(double %tmp.21)		 ; ty=int
	%tmp.22 = setne int %tmp.20, 0		 ; ty=bool
	%tmp.23 = cast bool %tmp.22 to int		 ; ty=int
	br label %shortcirc_done.2
shortcirc_done.2:
	%shortcirc_val.2 = phi bool [ false, %endif.0 ], [ %tmp.22, %shortcirc_next.2 ]		 ; ty=bool
	%tmp.24 = cast bool %shortcirc_val.2 to int		 ; ty=int
	br bool %shortcirc_val.2, label %then.1, label %endif.1
then.1:
	store %RPyFREXP_RESULT* null, %RPyFREXP_RESULT** %result
	br label %return
after_ret.0:
	br label %endif.1
endif.1:
	%tmp.26 = load double* %m		 ; ty=double
	%tmp.27 = load int* %expo		 ; ty=int
	%tmp.25 = call fastcc %RPyFREXP_RESULT* (double, int)* %ll_frexp_result__Float_Signed(double %tmp.26, int %tmp.27)		 ; ty=%RPyFREXP_RESULT*
	store %RPyFREXP_RESULT* %tmp.25, %RPyFREXP_RESULT** %result
	br label %return
after_ret.1:
	br label %return
return:
	%tmp.28 = load %RPyFREXP_RESULT** %result		 ; ty=%RPyFREXP_RESULT*
	ret %RPyFREXP_RESULT* %tmp.28
}

""")


