
implementation

;implementation of space operations for simple types


declare void %llvm.memmove(sbyte*, sbyte*, uint, uint)
declare void %llvm.memcpy(sbyte*, sbyte*, uint, uint)
declare void %llvm.memset(sbyte*, ubyte, uint, uint)




;Basic operations for ints
internal int %std.add(int %a, int %b) {
	%r = add int %a, %b
	ret int %r
}

internal int %std.inplace_add(int %a, int %b) {
	%r = add int %a, %b	
	ret int %r
}

internal int %std.sub(int %a, int %b) {
	%r = sub int %a, %b
	ret int %r
}

internal int %std.inplace_sub(int %a, int %b) {
	%r = sub int %a, %b
	ret int %r
}

internal int %std.mul(int %a, int %b) {
	%r = mul int %a, %b	
	ret int %r
}

internal int %std.inplace_mul(int %a, int %b) {
	%r = mul int %a, %b
	ret int %r
}

internal int %std.div(int %a, int %b) {
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_div(int %a, int %b) {
	%r = div int %a, %b
	ret int %r
}

internal int %std.floordiv(int %a, int %b) {
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_floordiv(int %a, int %b) {
	%r = div int %a, %b
	ret int %r
}

internal int %std.mod(int %a, int %b) {
	%r = rem int %a, %b	
	ret int %r
}

internal int %std.inplace_mod(int %a, int %b) {
	%r = rem int %a, %b	
	ret int %r
}

;Basic operations for doubles
internal double %std.add(double %a, double %b) {
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(double %a, double %b) {
	%r = add double %a, %b	
	ret double %r
}

internal double %std.sub(double %a, double %b) {
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(double %a, double %b) {
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(double %a, double %b) {
	%r = mul double %a, %b	
	ret double %r
}

internal double %std.inplace_mul(double %a, double %b) {
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(double %a, double %b) {
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(double %a, double %b) {
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(double %a, double %b) {
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_floordiv(double %a, double %b) {
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(double %a, double %b) {
	%r = rem double %a, %b	
	ret double %r
}

internal double %std.inplace_mod(double %a, double %b) {
	%r = rem double %a, %b	
	ret double %r
}

;Basic comparisons for doubles

internal bool %std.is(double %a, double %b) {
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.is_true(double %a) {
	%b = cast double %a to bool
	ret bool %b
}

internal bool %std.eq(double %a, double %b) {
	%r = seteq double %a, %b	
	ret bool %r
}

internal bool %std.neq(double %a, double %b) {
	%r = seteq double %a, %b	
	%r1 = xor bool %r, true
	ret bool %r1
}

internal bool %std.lt(double %a, double %b) {
	%r = setlt double %a, %b	
	ret bool %r
}

internal bool %std.gt(double %a, double %b) {
	%r = setgt double %a, %b	
	ret bool %r
}

internal bool %std.le(double %a, double %b) {
	%r = setle double %a, %b	
	ret bool %r
}

internal bool %std.ge(double %a, double %b) {
	%r = setge double %a, %b	
	ret bool %r
}

;Basic comparisons for ints

internal bool %std.is(int %a, int %b) {
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.is_true(int %a) {
	%b = cast int %a to bool
	ret bool %b
}

internal bool %std.eq(int %a, int %b) {
	%r = seteq int %a, %b	
	ret bool %r
}

internal bool %std.neq(int %a, int %b) {
	%r = seteq int %a, %b	
	%r1 = xor bool %r, true
	ret bool %r1
}

internal bool %std.lt(int %a, int %b) {
	%r = setlt int %a, %b	
	ret bool %r
}

internal bool %std.gt(int %a, int %b) {
	%r = setgt int %a, %b	
	ret bool %r
}

internal bool %std.le(int %a, int %b) {
	%r = setle int %a, %b	
	ret bool %r
}

internal bool %std.ge(int %a, int %b) {
	%r = setge int %a, %b	
	ret bool %r
}


;Logical operations for ints

internal int %std.and_(int %a, int %b) {
	%r = and int %a, %b
	ret int %r
}

internal int %std.inplace_and(int %a, int %b) {
	%r = and int %a, %b
	ret int %r
}

internal int %std.or(int %a, int %b) {
	%r = or int %a, %b
	ret int %r
}

internal int %std.inplace_or(int %a, int %b) {
	%r = or int %a, %b
	ret int %r
}

internal int %std.xor(int %a, int %b) {
	%r = xor int %a, %b
	ret int %r
}

internal int %std.inplace_xor(int %a, int %b) {
	%r = xor int %a, %b
	ret int %r
}

internal int %std.lshift(int %a, int %b) {
	%shift = cast int %b to ubyte
	%r = shl int %a, ubyte %shift
	ret int %r
}

internal int %std.rshift(int %a, int %b) {
	%shift = cast int %b to ubyte
	%r = shr int %a, ubyte %shift
	ret int %r
}


;bools
internal bool %std.is_true(bool %a) {
	ret bool %a
}

internal bool %std.and(bool %a, bool %b) {
	%r = and bool %a, %b	
	ret bool %r
}

internal bool %std.or(bool %a, bool %b) {
	%r = or bool %a, %b	
	ret bool %r
}

