;types for type info at runtime

%std.class = type {%std.class*, uint}
%std.object = type {%std.class*}


implementation


;functions for type info at runtime

bool %std.issubtype(%std.class* %a, %std.class* %b) {
entry:
	br label %not_null		
not_null:
	%curr_a = phi %std.class* [%a, %entry], [%base, %recurse]
	%n = seteq %std.class* %curr_a, null
	br bool %n, label %return, label %if
if:
	%same = seteq %std.class* %curr_a, %b
	br bool %same, label %return, label %recurse
recurse:
	%baseptr = getelementptr %std.class* %curr_a, int 0, uint 0
	%base = load %std.class** %baseptr
	br label %not_null
return:
	%result = phi bool [false, %not_null], [true, %if]
	ret bool %result
}

bool %std.isinstance(%std.object* %a, %std.class* %b) {
entry:
	%baseptr = getelementptr %std.object* %a, int 0, uint 0
	%class = load %std.class** %baseptr
	%result = call bool %std.issubtype(%std.class* %class, %std.class* %b)
	ret bool %result
}



