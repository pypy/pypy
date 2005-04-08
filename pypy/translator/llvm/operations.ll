implementation
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
	%a = cast double %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(double %a, double %b) {
	%a = cast double %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(double %a, double %b) {
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(double %a, double %b) {
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

internal bool %std.is_(double %a, double %b) {
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(double %a, double %b) {
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(double %a, double %b) {
	%r = setlt double %a, %b
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

internal bool %std.gt(double %a, double %b) {
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(double %a, double %b) {
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(double %a, uint %b) {
	%b = cast uint %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(double %a, uint %b) {
	%b = cast uint %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(double %a, uint %b) {
	%b = cast uint %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(double %a, uint %b) {
	%b = cast uint %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(double %a, uint %b) {
	%b = cast uint %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(double %a, uint %b) {
	%b = cast uint %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(double %a, uint %b) {
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(double %a, uint %b) {
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(double %a, uint %b) {
	%a = cast double %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(double %a, uint %b) {
	%a = cast double %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(double %a, uint %b) {
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(double %a, uint %b) {
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(double %a, uint %b) {
	%b = cast uint %b to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(double %a, uint %b) {
	%b = cast uint %b to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(double %a, uint %b) {
	%b = cast uint %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(double %a, uint %b) {
	%b = cast uint %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(double %a, uint %b) {
	%b = cast uint %b to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(double %a, uint %b) {
	%b = cast uint %b to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(double %a, uint %b) {
	%b = cast uint %b to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(double %a, uint %b) {
	%b = cast uint %b to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(double %a, uint %b) {
	%b = cast uint %b to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(double %a, int %b) {
	%b = cast int %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(double %a, int %b) {
	%b = cast int %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(double %a, int %b) {
	%b = cast int %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(double %a, int %b) {
	%b = cast int %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(double %a, int %b) {
	%b = cast int %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(double %a, int %b) {
	%b = cast int %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(double %a, int %b) {
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(double %a, int %b) {
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(double %a, int %b) {
	%a = cast double %a to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(double %a, int %b) {
	%a = cast double %a to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(double %a, int %b) {
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(double %a, int %b) {
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(double %a, int %b) {
	%b = cast int %b to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(double %a, int %b) {
	%b = cast int %b to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(double %a, int %b) {
	%b = cast int %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(double %a, int %b) {
	%b = cast int %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(double %a, int %b) {
	%b = cast int %b to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(double %a, int %b) {
	%b = cast int %b to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(double %a, int %b) {
	%b = cast int %b to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(double %a, int %b) {
	%b = cast int %b to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(double %a, int %b) {
	%b = cast int %b to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(double %a, bool %b) {
	%b = cast bool %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(double %a, bool %b) {
	%b = cast bool %b to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(double %a, bool %b) {
	%b = cast bool %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(double %a, bool %b) {
	%b = cast bool %b to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(double %a, bool %b) {
	%b = cast bool %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(double %a, bool %b) {
	%b = cast bool %b to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(double %a, bool %b) {
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(double %a, bool %b) {
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(double %a, bool %b) {
	%a = cast double %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(double %a, bool %b) {
	%a = cast double %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(double %a, bool %b) {
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(double %a, bool %b) {
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(double %a, bool %b) {
	%b = cast bool %b to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(double %a, bool %b) {
	%b = cast bool %b to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(double %a, bool %b) {
	%b = cast bool %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(double %a, bool %b) {
	%b = cast bool %b to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(double %a, bool %b) {
	%b = cast bool %b to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(double %a, bool %b) {
	%b = cast bool %b to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(double %a, bool %b) {
	%b = cast bool %b to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(double %a, bool %b) {
	%b = cast bool %b to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(double %a, bool %b) {
	%b = cast bool %b to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(uint %a, double %b) {
	%a = cast uint %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(uint %a, double %b) {
	%a = cast uint %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(uint %a, double %b) {
	%a = cast uint %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(uint %a, double %b) {
	%a = cast uint %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(uint %a, double %b) {
	%a = cast uint %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(uint %a, double %b) {
	%a = cast uint %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(uint %a, double %b) {
	%a = cast uint %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(uint %a, double %b) {
	%a = cast uint %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(uint %a, double %b) {
	%a = cast uint %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(uint %a, double %b) {
	%a = cast uint %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(uint %a, double %b) {
	%a = cast uint %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(uint %a, double %b) {
	%a = cast uint %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(uint %a, double %b) {
	%a = cast uint %a to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(uint %a, double %b) {
	%a = cast uint %a to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(uint %a, double %b) {
	%a = cast uint %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(uint %a, double %b) {
	%a = cast uint %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(uint %a, double %b) {
	%a = cast uint %a to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(uint %a, double %b) {
	%a = cast uint %a to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(uint %a, double %b) {
	%a = cast uint %a to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(uint %a, double %b) {
	%a = cast uint %a to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(uint %a, double %b) {
	%a = cast uint %a to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.add(uint %a, uint %b) {
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.inplace_add(uint %a, uint %b) {
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.sub(uint %a, uint %b) {
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.inplace_sub(uint %a, uint %b) {
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.mul(uint %a, uint %b) {
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mul(uint %a, uint %b) {
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.div(uint %a, uint %b) {
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.inplace_div(uint %a, uint %b) {
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.floordiv(uint %a, uint %b) {
	%a = cast uint %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal uint %std.inplace_floordiv(uint %a, uint %b) {
	%a = cast uint %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal double %std.truediv(uint %a, uint %b) {
	%a = cast uint %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(uint %a, uint %b) {
	%a = cast uint %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal uint %std.mod(uint %a, uint %b) {
	%r = rem uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mod(uint %a, uint %b) {
	%r = rem uint %a, %b
	ret uint %r
}

internal bool %std.is_(uint %a, uint %b) {
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.eq(uint %a, uint %b) {
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.lt(uint %a, uint %b) {
	%r = setlt uint %a, %b
	ret bool %r
}

internal bool %std.le(uint %a, uint %b) {
	%r = setle uint %a, %b
	ret bool %r
}

internal bool %std.ge(uint %a, uint %b) {
	%r = setge uint %a, %b
	ret bool %r
}

internal bool %std.gt(uint %a, uint %b) {
	%r = setgt uint %a, %b
	ret bool %r
}

internal bool %std.neq(uint %a, uint %b) {
	%r = setgt uint %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.add(uint %a, int %b) {
	%b = cast int %b to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.inplace_add(uint %a, int %b) {
	%b = cast int %b to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.sub(uint %a, int %b) {
	%b = cast int %b to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.inplace_sub(uint %a, int %b) {
	%b = cast int %b to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.mul(uint %a, int %b) {
	%b = cast int %b to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mul(uint %a, int %b) {
	%b = cast int %b to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.div(uint %a, int %b) {
	%b = cast int %b to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.inplace_div(uint %a, int %b) {
	%b = cast int %b to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.floordiv(uint %a, int %b) {
	%a = cast uint %a to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal uint %std.inplace_floordiv(uint %a, int %b) {
	%a = cast uint %a to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal double %std.truediv(uint %a, int %b) {
	%a = cast uint %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(uint %a, int %b) {
	%a = cast uint %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal uint %std.mod(uint %a, int %b) {
	%b = cast int %b to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mod(uint %a, int %b) {
	%b = cast int %b to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal bool %std.is_(uint %a, int %b) {
	%b = cast int %b to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.eq(uint %a, int %b) {
	%b = cast int %b to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.lt(uint %a, int %b) {
	%b = cast int %b to uint
	%r = setlt uint %a, %b
	ret bool %r
}

internal bool %std.le(uint %a, int %b) {
	%b = cast int %b to uint
	%r = setle uint %a, %b
	ret bool %r
}

internal bool %std.ge(uint %a, int %b) {
	%b = cast int %b to uint
	%r = setge uint %a, %b
	ret bool %r
}

internal bool %std.gt(uint %a, int %b) {
	%b = cast int %b to uint
	%r = setgt uint %a, %b
	ret bool %r
}

internal bool %std.neq(uint %a, int %b) {
	%b = cast int %b to uint
	%r = setgt uint %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.add(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.inplace_add(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.sub(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.inplace_sub(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.mul(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mul(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.div(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.inplace_div(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.floordiv(uint %a, bool %b) {
	%a = cast uint %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal uint %std.inplace_floordiv(uint %a, bool %b) {
	%a = cast uint %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal double %std.truediv(uint %a, bool %b) {
	%a = cast uint %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(uint %a, bool %b) {
	%a = cast uint %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal uint %std.mod(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mod(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal bool %std.is_(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.eq(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.lt(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = setlt uint %a, %b
	ret bool %r
}

internal bool %std.le(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = setle uint %a, %b
	ret bool %r
}

internal bool %std.ge(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = setge uint %a, %b
	ret bool %r
}

internal bool %std.gt(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = setgt uint %a, %b
	ret bool %r
}

internal bool %std.neq(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = setgt uint %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(int %a, double %b) {
	%a = cast int %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(int %a, double %b) {
	%a = cast int %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(int %a, double %b) {
	%a = cast int %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(int %a, double %b) {
	%a = cast int %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(int %a, double %b) {
	%a = cast int %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(int %a, double %b) {
	%a = cast int %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(int %a, double %b) {
	%a = cast int %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(int %a, double %b) {
	%a = cast int %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(int %a, double %b) {
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(int %a, double %b) {
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(int %a, double %b) {
	%a = cast int %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(int %a, double %b) {
	%a = cast int %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(int %a, double %b) {
	%a = cast int %a to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(int %a, double %b) {
	%a = cast int %a to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(int %a, double %b) {
	%a = cast int %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(int %a, double %b) {
	%a = cast int %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(int %a, double %b) {
	%a = cast int %a to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(int %a, double %b) {
	%a = cast int %a to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(int %a, double %b) {
	%a = cast int %a to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(int %a, double %b) {
	%a = cast int %a to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(int %a, double %b) {
	%a = cast int %a to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.add(int %a, uint %b) {
	%a = cast int %a to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.inplace_add(int %a, uint %b) {
	%a = cast int %a to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.sub(int %a, uint %b) {
	%a = cast int %a to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.inplace_sub(int %a, uint %b) {
	%a = cast int %a to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.mul(int %a, uint %b) {
	%a = cast int %a to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mul(int %a, uint %b) {
	%a = cast int %a to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.div(int %a, uint %b) {
	%a = cast int %a to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.inplace_div(int %a, uint %b) {
	%a = cast int %a to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.floordiv(int %a, uint %b) {
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal uint %std.inplace_floordiv(int %a, uint %b) {
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal double %std.truediv(int %a, uint %b) {
	%a = cast int %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(int %a, uint %b) {
	%a = cast int %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal uint %std.mod(int %a, uint %b) {
	%a = cast int %a to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mod(int %a, uint %b) {
	%a = cast int %a to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal bool %std.is_(int %a, uint %b) {
	%a = cast int %a to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.eq(int %a, uint %b) {
	%a = cast int %a to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.lt(int %a, uint %b) {
	%a = cast int %a to uint
	%r = setlt uint %a, %b
	ret bool %r
}

internal bool %std.le(int %a, uint %b) {
	%a = cast int %a to uint
	%r = setle uint %a, %b
	ret bool %r
}

internal bool %std.ge(int %a, uint %b) {
	%a = cast int %a to uint
	%r = setge uint %a, %b
	ret bool %r
}

internal bool %std.gt(int %a, uint %b) {
	%a = cast int %a to uint
	%r = setgt uint %a, %b
	ret bool %r
}

internal bool %std.neq(int %a, uint %b) {
	%a = cast int %a to uint
	%r = setgt uint %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

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

internal double %std.truediv(int %a, int %b) {
	%a = cast int %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(int %a, int %b) {
	%a = cast int %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal int %std.mod(int %a, int %b) {
	%r = rem int %a, %b
	ret int %r
}

internal int %std.inplace_mod(int %a, int %b) {
	%r = rem int %a, %b
	ret int %r
}

internal bool %std.is_(int %a, int %b) {
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.eq(int %a, int %b) {
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.lt(int %a, int %b) {
	%r = setlt int %a, %b
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

internal bool %std.gt(int %a, int %b) {
	%r = setgt int %a, %b
	ret bool %r
}

internal bool %std.neq(int %a, int %b) {
	%r = setgt int %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal int %std.add(int %a, bool %b) {
	%b = cast bool %b to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.inplace_add(int %a, bool %b) {
	%b = cast bool %b to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.sub(int %a, bool %b) {
	%b = cast bool %b to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.inplace_sub(int %a, bool %b) {
	%b = cast bool %b to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.mul(int %a, bool %b) {
	%b = cast bool %b to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.inplace_mul(int %a, bool %b) {
	%b = cast bool %b to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.div(int %a, bool %b) {
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_div(int %a, bool %b) {
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.floordiv(int %a, bool %b) {
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_floordiv(int %a, bool %b) {
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal double %std.truediv(int %a, bool %b) {
	%a = cast int %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(int %a, bool %b) {
	%a = cast int %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal int %std.mod(int %a, bool %b) {
	%b = cast bool %b to int
	%r = rem int %a, %b
	ret int %r
}

internal int %std.inplace_mod(int %a, bool %b) {
	%b = cast bool %b to int
	%r = rem int %a, %b
	ret int %r
}

internal bool %std.is_(int %a, bool %b) {
	%b = cast bool %b to int
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.eq(int %a, bool %b) {
	%b = cast bool %b to int
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.lt(int %a, bool %b) {
	%b = cast bool %b to int
	%r = setlt int %a, %b
	ret bool %r
}

internal bool %std.le(int %a, bool %b) {
	%b = cast bool %b to int
	%r = setle int %a, %b
	ret bool %r
}

internal bool %std.ge(int %a, bool %b) {
	%b = cast bool %b to int
	%r = setge int %a, %b
	ret bool %r
}

internal bool %std.gt(int %a, bool %b) {
	%b = cast bool %b to int
	%r = setgt int %a, %b
	ret bool %r
}

internal bool %std.neq(int %a, bool %b) {
	%b = cast bool %b to int
	%r = setgt int %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal double %std.add(bool %a, double %b) {
	%a = cast bool %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.inplace_add(bool %a, double %b) {
	%a = cast bool %a to double
	%r = add double %a, %b
	ret double %r
}

internal double %std.sub(bool %a, double %b) {
	%a = cast bool %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.inplace_sub(bool %a, double %b) {
	%a = cast bool %a to double
	%r = sub double %a, %b
	ret double %r
}

internal double %std.mul(bool %a, double %b) {
	%a = cast bool %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.inplace_mul(bool %a, double %b) {
	%a = cast bool %a to double
	%r = mul double %a, %b
	ret double %r
}

internal double %std.div(bool %a, double %b) {
	%a = cast bool %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_div(bool %a, double %b) {
	%a = cast bool %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.floordiv(bool %a, double %b) {
	%a = cast bool %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.inplace_floordiv(bool %a, double %b) {
	%a = cast bool %a to int
	%b = cast double %b to int
	%r = div int %a, %b
	%r = cast int %r to double
	ret double %r
}

internal double %std.truediv(bool %a, double %b) {
	%a = cast bool %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(bool %a, double %b) {
	%a = cast bool %a to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.mod(bool %a, double %b) {
	%a = cast bool %a to double
	%r = rem double %a, %b
	ret double %r
}

internal double %std.inplace_mod(bool %a, double %b) {
	%a = cast bool %a to double
	%r = rem double %a, %b
	ret double %r
}

internal bool %std.is_(bool %a, double %b) {
	%a = cast bool %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.eq(bool %a, double %b) {
	%a = cast bool %a to double
	%r = seteq double %a, %b
	ret bool %r
}

internal bool %std.lt(bool %a, double %b) {
	%a = cast bool %a to double
	%r = setlt double %a, %b
	ret bool %r
}

internal bool %std.le(bool %a, double %b) {
	%a = cast bool %a to double
	%r = setle double %a, %b
	ret bool %r
}

internal bool %std.ge(bool %a, double %b) {
	%a = cast bool %a to double
	%r = setge double %a, %b
	ret bool %r
}

internal bool %std.gt(bool %a, double %b) {
	%a = cast bool %a to double
	%r = setgt double %a, %b
	ret bool %r
}

internal bool %std.neq(bool %a, double %b) {
	%a = cast bool %a to double
	%r = setgt double %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.add(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.inplace_add(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = add uint %a, %b
	ret uint %r
}

internal uint %std.sub(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.inplace_sub(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = sub uint %a, %b
	ret uint %r
}

internal uint %std.mul(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mul(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = mul uint %a, %b
	ret uint %r
}

internal uint %std.div(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.inplace_div(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = div uint %a, %b
	ret uint %r
}

internal uint %std.floordiv(bool %a, uint %b) {
	%a = cast bool %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal uint %std.inplace_floordiv(bool %a, uint %b) {
	%a = cast bool %a to int
	%b = cast uint %b to int
	%r = div int %a, %b
	%r = cast int %r to uint
	ret uint %r
}

internal double %std.truediv(bool %a, uint %b) {
	%a = cast bool %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(bool %a, uint %b) {
	%a = cast bool %a to double
	%b = cast uint %b to double
	%r = div double %a, %b
	ret double %r
}

internal uint %std.mod(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal uint %std.inplace_mod(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = rem uint %a, %b
	ret uint %r
}

internal bool %std.is_(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.eq(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = seteq uint %a, %b
	ret bool %r
}

internal bool %std.lt(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = setlt uint %a, %b
	ret bool %r
}

internal bool %std.le(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = setle uint %a, %b
	ret bool %r
}

internal bool %std.ge(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = setge uint %a, %b
	ret bool %r
}

internal bool %std.gt(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = setgt uint %a, %b
	ret bool %r
}

internal bool %std.neq(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = setgt uint %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal int %std.add(bool %a, int %b) {
	%a = cast bool %a to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.inplace_add(bool %a, int %b) {
	%a = cast bool %a to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.sub(bool %a, int %b) {
	%a = cast bool %a to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.inplace_sub(bool %a, int %b) {
	%a = cast bool %a to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.mul(bool %a, int %b) {
	%a = cast bool %a to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.inplace_mul(bool %a, int %b) {
	%a = cast bool %a to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.div(bool %a, int %b) {
	%a = cast bool %a to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_div(bool %a, int %b) {
	%a = cast bool %a to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.floordiv(bool %a, int %b) {
	%a = cast bool %a to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_floordiv(bool %a, int %b) {
	%a = cast bool %a to int
	%r = div int %a, %b
	ret int %r
}

internal double %std.truediv(bool %a, int %b) {
	%a = cast bool %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(bool %a, int %b) {
	%a = cast bool %a to double
	%b = cast int %b to double
	%r = div double %a, %b
	ret double %r
}

internal int %std.mod(bool %a, int %b) {
	%a = cast bool %a to int
	%r = rem int %a, %b
	ret int %r
}

internal int %std.inplace_mod(bool %a, int %b) {
	%a = cast bool %a to int
	%r = rem int %a, %b
	ret int %r
}

internal bool %std.is_(bool %a, int %b) {
	%a = cast bool %a to int
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.eq(bool %a, int %b) {
	%a = cast bool %a to int
	%r = seteq int %a, %b
	ret bool %r
}

internal bool %std.lt(bool %a, int %b) {
	%a = cast bool %a to int
	%r = setlt int %a, %b
	ret bool %r
}

internal bool %std.le(bool %a, int %b) {
	%a = cast bool %a to int
	%r = setle int %a, %b
	ret bool %r
}

internal bool %std.ge(bool %a, int %b) {
	%a = cast bool %a to int
	%r = setge int %a, %b
	ret bool %r
}

internal bool %std.gt(bool %a, int %b) {
	%a = cast bool %a to int
	%r = setgt int %a, %b
	ret bool %r
}

internal bool %std.neq(bool %a, int %b) {
	%a = cast bool %a to int
	%r = setgt int %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal int %std.add(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.inplace_add(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = add int %a, %b
	ret int %r
}

internal int %std.sub(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.inplace_sub(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = sub int %a, %b
	ret int %r
}

internal int %std.mul(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.inplace_mul(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = mul int %a, %b
	ret int %r
}

internal int %std.div(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal int %std.inplace_div(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	ret int %r
}

internal bool %std.floordiv(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to bool
	ret bool %r
}

internal bool %std.inplace_floordiv(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = div int %a, %b
	%r = cast int %r to bool
	ret bool %r
}

internal double %std.truediv(bool %a, bool %b) {
	%a = cast bool %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal double %std.inplace_truediv(bool %a, bool %b) {
	%a = cast bool %a to double
	%b = cast bool %b to double
	%r = div double %a, %b
	ret double %r
}

internal int %std.mod(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = rem int %a, %b
	ret int %r
}

internal int %std.inplace_mod(bool %a, bool %b) {
	%a = cast bool %a to int
	%b = cast bool %b to int
	%r = rem int %a, %b
	ret int %r
}

internal bool %std.is_(bool %a, bool %b) {
	%r = seteq bool %a, %b
	ret bool %r
}

internal bool %std.eq(bool %a, bool %b) {
	%r = seteq bool %a, %b
	ret bool %r
}

internal bool %std.lt(bool %a, bool %b) {
	%r = setlt bool %a, %b
	ret bool %r
}

internal bool %std.le(bool %a, bool %b) {
	%r = setle bool %a, %b
	ret bool %r
}

internal bool %std.ge(bool %a, bool %b) {
	%r = setge bool %a, %b
	ret bool %r
}

internal bool %std.gt(bool %a, bool %b) {
	%r = setgt bool %a, %b
	ret bool %r
}

internal bool %std.neq(bool %a, bool %b) {
	%r = setgt bool %a, %b
	%r1 = xor bool %r, true
	ret bool %r1
}

internal uint %std.and_(uint %a, uint %b) {
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.inplace_and(uint %a, uint %b) {
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.or_(uint %a, uint %b) {
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.inplace_or(uint %a, uint %b) {
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.xor(uint %a, uint %b) {
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.inplace_xor(uint %a, uint %b) {
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.and_(uint %a, int %b) {
	%b = cast int %b to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.inplace_and(uint %a, int %b) {
	%b = cast int %b to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.or_(uint %a, int %b) {
	%b = cast int %b to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.inplace_or(uint %a, int %b) {
	%b = cast int %b to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.xor(uint %a, int %b) {
	%b = cast int %b to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.inplace_xor(uint %a, int %b) {
	%b = cast int %b to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.and_(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.inplace_and(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.or_(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.inplace_or(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.xor(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.inplace_xor(uint %a, bool %b) {
	%b = cast bool %b to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.and_(int %a, uint %b) {
	%a = cast int %a to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.inplace_and(int %a, uint %b) {
	%a = cast int %a to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.or_(int %a, uint %b) {
	%a = cast int %a to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.inplace_or(int %a, uint %b) {
	%a = cast int %a to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.xor(int %a, uint %b) {
	%a = cast int %a to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.inplace_xor(int %a, uint %b) {
	%a = cast int %a to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal int %std.and_(int %a, int %b) {
	%r = and int %a, %b
	ret int %r
}

internal int %std.inplace_and(int %a, int %b) {
	%r = and int %a, %b
	ret int %r
}

internal int %std.or_(int %a, int %b) {
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

internal int %std.and_(int %a, bool %b) {
	%b = cast bool %b to int
	%r = and int %a, %b
	ret int %r
}

internal int %std.inplace_and(int %a, bool %b) {
	%b = cast bool %b to int
	%r = and int %a, %b
	ret int %r
}

internal int %std.or_(int %a, bool %b) {
	%b = cast bool %b to int
	%r = or int %a, %b
	ret int %r
}

internal int %std.inplace_or(int %a, bool %b) {
	%b = cast bool %b to int
	%r = or int %a, %b
	ret int %r
}

internal int %std.xor(int %a, bool %b) {
	%b = cast bool %b to int
	%r = xor int %a, %b
	ret int %r
}

internal int %std.inplace_xor(int %a, bool %b) {
	%b = cast bool %b to int
	%r = xor int %a, %b
	ret int %r
}

internal uint %std.and_(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.inplace_and(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = and uint %a, %b
	ret uint %r
}

internal uint %std.or_(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.inplace_or(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = or uint %a, %b
	ret uint %r
}

internal uint %std.xor(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal uint %std.inplace_xor(bool %a, uint %b) {
	%a = cast bool %a to uint
	%r = xor uint %a, %b
	ret uint %r
}

internal int %std.and_(bool %a, int %b) {
	%a = cast bool %a to int
	%r = and int %a, %b
	ret int %r
}

internal int %std.inplace_and(bool %a, int %b) {
	%a = cast bool %a to int
	%r = and int %a, %b
	ret int %r
}

internal int %std.or_(bool %a, int %b) {
	%a = cast bool %a to int
	%r = or int %a, %b
	ret int %r
}

internal int %std.inplace_or(bool %a, int %b) {
	%a = cast bool %a to int
	%r = or int %a, %b
	ret int %r
}

internal int %std.xor(bool %a, int %b) {
	%a = cast bool %a to int
	%r = xor int %a, %b
	ret int %r
}

internal int %std.inplace_xor(bool %a, int %b) {
	%a = cast bool %a to int
	%r = xor int %a, %b
	ret int %r
}

internal bool %std.and_(bool %a, bool %b) {
	%r = and bool %a, %b
	ret bool %r
}

internal bool %std.inplace_and(bool %a, bool %b) {
	%r = and bool %a, %b
	ret bool %r
}

internal bool %std.or_(bool %a, bool %b) {
	%r = or bool %a, %b
	ret bool %r
}

internal bool %std.inplace_or(bool %a, bool %b) {
	%r = or bool %a, %b
	ret bool %r
}

internal bool %std.xor(bool %a, bool %b) {
	%r = xor bool %a, %b
	ret bool %r
}

internal bool %std.inplace_xor(bool %a, bool %b) {
	%r = xor bool %a, %b
	ret bool %r
}

internal uint %std.lshift(uint %a, uint %b) {
	%b = cast uint %b to ubyte
	%r = shl uint %a, ubyte %b
	ret uint %r
}

internal uint %std.rshift(uint %a, uint %b) {
	%b = cast uint %b to ubyte
	%r = shr uint %a, ubyte %b
	ret uint %r
}

internal uint %std.lshift(uint %a, int %b) {
	%b = cast int %b to ubyte
	%r = shl uint %a, ubyte %b
	ret uint %r
}

internal uint %std.rshift(uint %a, int %b) {
	%b = cast int %b to ubyte
	%r = shr uint %a, ubyte %b
	ret uint %r
}

internal int %std.lshift(int %a, uint %b) {
	%b = cast uint %b to ubyte
	%r = shl int %a, ubyte %b
	ret int %r
}

internal int %std.rshift(int %a, uint %b) {
	%b = cast uint %b to ubyte
	%r = shr int %a, ubyte %b
	ret int %r
}

internal int %std.lshift(int %a, int %b) {
	%b = cast int %b to ubyte
	%r = shl int %a, ubyte %b
	ret int %r
}

internal int %std.rshift(int %a, int %b) {
	%b = cast int %b to ubyte
	%r = shr int %a, ubyte %b
	ret int %r
}

internal int %std.int(double %a) {
	%r = cast double %a to int
	ret int %r
}

internal bool %std.bool(double %a) {
	%r = cast double %a to bool
	ret bool %r
}

internal bool %std.is_true(double %a) {
	%r = cast double %a to bool
	ret bool %r
}

internal int %std.int(uint %a) {
	%r = cast uint %a to int
	ret int %r
}

internal bool %std.bool(uint %a) {
	%r = cast uint %a to bool
	ret bool %r
}

internal bool %std.is_true(uint %a) {
	%r = cast uint %a to bool
	ret bool %r
}

internal int %std.int(int %a) {
	%r = cast int %a to int
	ret int %r
}

internal bool %std.bool(int %a) {
	%r = cast int %a to bool
	ret bool %r
}

internal bool %std.is_true(int %a) {
	%r = cast int %a to bool
	ret bool %r
}

internal int %std.int(bool %a) {
	%r = cast bool %a to int
	ret int %r
}

internal bool %std.bool(bool %a) {
	%r = cast bool %a to bool
	ret bool %r
}

internal bool %std.is_true(bool %a) {
	%r = cast bool %a to bool
	ret bool %r
}

