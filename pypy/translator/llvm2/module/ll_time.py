extdeclarations = '''
;ll_time.py

%struct.timeval = type { int, int }
%struct.timezone = type { int, int }
%typedef.fd_set = type { [32 x int] }

%.str_xxx1 = internal constant [16 x sbyte] c"select() failed\\00"		; <[16 x sbyte]*> [#uses=1]

declare ccc double %floor(double)
declare ccc double %fmod(double, double)
declare ccc int %clock()
declare ccc int %select(int, %typedef.fd_set*, %typedef.fd_set*, %typedef.fd_set*, %struct.timeval*)
declare ccc int %gettimeofday(%struct.timeval*, %struct.timeval*)
declare ccc int %time( int* )
'''

extfunctions = {}

extfunctions["%ll_time_time"] = ((), """

internal fastcc double %ll_time_time() {
	%t = alloca %struct.timeval		; <%struct.timeval*> [#uses=3]
	%secs = alloca int		; <int*> [#uses=2]
	%tmp.0 = call int %gettimeofday( %struct.timeval* %t, %struct.timeval* null )		; <int> [#uses=1]
	%tmp.1 = seteq int %tmp.0, 0		; <bool> [#uses=2]
	%tmp.2 = cast bool %tmp.1 to int		; <int> [#uses=0]
	br bool %tmp.1, label %then, label %endif

then:		; preds = %entry
	%tmp.3 = getelementptr %struct.timeval* %t, int 0, uint 0		; <int*> [#uses=1]
	%tmp.4 = load int* %tmp.3		; <int> [#uses=1]
	%tmp.5 = cast int %tmp.4 to double		; <double> [#uses=1]
	%tmp.6 = getelementptr %struct.timeval* %t, int 0, uint 1		; <int*> [#uses=1]
	%tmp.7 = load int* %tmp.6		; <int> [#uses=1]
	%tmp.8 = cast int %tmp.7 to double		; <double> [#uses=1]
	%tmp.9 = mul double %tmp.8, 1.000000e-06		; <double> [#uses=1]
	%tmp.10 = add double %tmp.5, %tmp.9		; <double> [#uses=1]
	ret double %tmp.10

endif:		; preds = %entry
	%tmp.11 = call int %time( int* %secs )		; <int> [#uses=0]
	%tmp.12 = load int* %secs		; <int> [#uses=1]
	%tmp.13 = cast int %tmp.12 to double		; <double> [#uses=1]
	ret double %tmp.13
}
""")

extfunctions["%ll_time_clock"] = ((), """
internal fastcc double %ll_time_clock() {
entry:
	%tmp.0 = call int %clock( )		; <int> [#uses=1]
	%tmp.1 = cast int %tmp.0 to double		; <double> [#uses=1]
	%tmp.2 = div double %tmp.1, 1.000000e+06		; <double> [#uses=1]
	ret double %tmp.2
}
""")

extfunctions["%ll_time_sleep"] = ((), """
internal fastcc void %ll_time_sleep(double %secs) {
entry:
	%t = alloca %struct.timeval		; <%struct.timeval*> [#uses=3]
	%tmp.0 = call double %fmod( double %secs, double 1.000000e+00 )		; <double> [#uses=1]
	%tmp.2 = call double %floor( double %secs )		; <double> [#uses=1]
	%tmp.4 = getelementptr %struct.timeval* %t, int 0, uint 0		; <int*> [#uses=1]
	%tmp.6 = cast double %tmp.2 to int		; <int> [#uses=1]
	store int %tmp.6, int* %tmp.4
	%tmp.7 = getelementptr %struct.timeval* %t, int 0, uint 1		; <int*> [#uses=1]
	%tmp.9 = mul double %tmp.0, 1.000000e+06		; <double> [#uses=1]
	%tmp.10 = cast double %tmp.9 to int		; <int> [#uses=1]
	store int %tmp.10, int* %tmp.7
	%tmp.11 = call int %select( int 0, %typedef.fd_set* null, %typedef.fd_set* null, %typedef.fd_set* null, %struct.timeval* %t )		; <int> [#uses=1]
	%tmp.12 = setne int %tmp.11, 0		; <bool> [#uses=2]
	%tmp.13 = cast bool %tmp.12 to int		; <int> [#uses=0]
	br bool %tmp.12, label %then.1, label %return

then.1:		; preds = %entry
	; XXX disabled for now: call void %RaiseSimpleException( int 1, sbyte* getelementptr ([16 x sbyte]* %.str_xxx1, int 0, int 0) )
	ret void

return:		; preds = %entry
	ret void
}
""")
