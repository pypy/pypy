

internal void %std.copy(%(item)s* %from, %(item)s* %to, uint %length) {
entry:
	%tmp.25 = seteq uint %length, 0
	br bool %tmp.25, label %return, label %no_exit

no_exit:
	%i.0.0 = phi uint [ %tmp.14, %no_exit ], [ 0, %entry ]
	%tmp.7 = getelementptr %(item)s* %to, uint %i.0.0
	%tmp.11 = getelementptr %(item)s* %from, uint %i.0.0
	%tmp.12 = load %(item)s* %tmp.11
	store %(item)s %tmp.12, %(item)s* %tmp.7
	%tmp.14 = add uint %i.0.0, 1
	%tmp.2 = setlt uint %tmp.14, %length
	br bool %tmp.2, label %no_exit, label %return

return:
	ret void
}

internal int %std.len(%std.list.%(name)s* %l) {
entry:
	%tmp.1 = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.2 = load uint* %tmp.1
	%tmp.3 = cast uint %tmp.2 to int
	ret int %tmp.3
}

internal int %std.valid_index(int %i, %std.list.%(name)s* %l) {
entry:
	%tmp.1 = setlt int %i, 0
	br bool %tmp.1, label %UnifiedReturnBlock, label %endif.0

endif.0:
	%tmp.1.i = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.2.i = load uint* %tmp.1.i
	%tmp.3.i = cast uint %tmp.2.i to int
	%not.tmp.6 = setgt int %tmp.3.i, %i
	%retval = cast bool %not.tmp.6 to int
	ret int %retval

UnifiedReturnBlock:
	ret int 0
}

internal %std.list.%(name)s* %std.newlist() {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint 0, uint* %tmp.3
	%tmp.5 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	store %(item)s* null, %(item)s** %tmp.5
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.newlist(%(item)s %value) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint 1, uint* %tmp.3
	%tmp.5 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.6 = malloc %(item)s
	store %(item)s* %tmp.6, %(item)s** %tmp.5
	store %(item)s %value, %(item)s* %tmp.6
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.newlist(%(item)s %v1, %(item)s %v2) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint 2, uint* %tmp.3
	%tmp.5 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.6 = malloc [2 x %(item)s]
	%tmp.6.sub = getelementptr [2 x %(item)s]* %tmp.6, int 0, int 0
	store %(item)s* %tmp.6.sub, %(item)s** %tmp.5
	store %(item)s %v1, %(item)s* %tmp.6.sub
	%tmp.16 = getelementptr [2 x %(item)s]* %tmp.6, int 0, int 1
	store %(item)s %v2, %(item)s* %tmp.16
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.newlist(%(item)s %v1, %(item)s %v2, %(item)s %v3) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint 3, uint* %tmp.3
	%tmp.5 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.6 = malloc [3 x %(item)s]
	%tmp.6.sub = getelementptr [3 x %(item)s]* %tmp.6, int 0, int 0
	store %(item)s* %tmp.6.sub, %(item)s** %tmp.5
	store %(item)s %v1, %(item)s* %tmp.6.sub
	%tmp.16 = getelementptr [3 x %(item)s]* %tmp.6, int 0, int 1
	store %(item)s %v2, %(item)s* %tmp.16
	%tmp.21 = getelementptr [3 x %(item)s]* %tmp.6, int 0, int 2
	store %(item)s %v3, %(item)s* %tmp.21
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.newlist(%(item)s %v1, %(item)s %v2, %(item)s %v3, %(item)s %v4) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint 4, uint* %tmp.3
	%tmp.5 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.6 = malloc [4 x %(item)s]
	%tmp.6.sub = getelementptr [4 x %(item)s]* %tmp.6, int 0, int 0
	store %(item)s* %tmp.6.sub, %(item)s** %tmp.5
	store %(item)s %v1, %(item)s* %tmp.6.sub
	%tmp.16 = getelementptr [4 x %(item)s]* %tmp.6, int 0, int 1
	store %(item)s %v2, %(item)s* %tmp.16
	%tmp.21 = getelementptr [4 x %(item)s]* %tmp.6, int 0, int 2
	store %(item)s %v3, %(item)s* %tmp.21
	%tmp.26 = getelementptr [4 x %(item)s]* %tmp.6, int 0, int 3
	store %(item)s %v4, %(item)s* %tmp.26
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.alloc_and_set(int %length, %(item)s %init) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	%tmp.5 = cast int %length to uint
	store uint %tmp.5, uint* %tmp.3
	%tmp.7 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.8 = malloc %(item)s, uint %tmp.5
	store %(item)s* %tmp.8, %(item)s** %tmp.7
	%tmp.165 = seteq int %length, 0
	br bool %tmp.165, label %loopexit, label %no_exit

no_exit:
	%i.0.0 = phi uint [ %tmp.26, %no_exit ], [ 0, %entry ]
	%tmp.20 = load %(item)s** %tmp.7
	%tmp.23 = getelementptr %(item)s* %tmp.20, uint %i.0.0
	store %(item)s %init, %(item)s* %tmp.23
	%tmp.26 = add uint %i.0.0, 1
	%tmp.16 = setgt uint %tmp.5, %tmp.26
	br bool %tmp.16, label %no_exit, label %loopexit

loopexit:
	ret %std.list.%(name)s* %tmp.0
}

internal %(item)s %std.getitem(%std.list.%(name)s* %l, int %index.1) {
entry:
	%tmp.1 = setlt int %index.1, 0
	%tmp.11 = getelementptr %std.list.%(name)s* %l, int 0, uint 1
	br bool %tmp.1, label %then, label %endif

then:
	%tmp.4 = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	%tmp.121 = load %(item)s** %tmp.11
	%tmp.142 = getelementptr %(item)s* %tmp.121, int %tmp.9
	%tmp.153 = load %(item)s* %tmp.142
	ret %(item)s %tmp.153

endif:
	%tmp.12 = load %(item)s** %tmp.11
	%tmp.14 = getelementptr %(item)s* %tmp.12, int %index.1
	%tmp.15 = load %(item)s* %tmp.14
	ret %(item)s %tmp.15
}

internal %(item)s %std.getitem.exc(%std.list.%(name)s* %l, int %index.1) {
entry:
	%tmp.1 = setlt int %index.1, 0
	br bool %tmp.1, label %then.0, label %endif.0.i

then.0:
	%tmp.4 = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	%tmp.1.i5 = setlt int %tmp.9, 0
	br bool %tmp.1.i5, label %then.1, label %endif.0.i

endif.0.i:
	%index_addr.0.0 = phi int [ %tmp.9, %then.0 ], [ %index.1, %entry ]
	%tmp.1.i.i = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.2.i.i = load uint* %tmp.1.i.i
	%tmp.3.i.i = cast uint %tmp.2.i.i to int
	%tmp.6.i = setgt int %tmp.3.i.i, %index_addr.0.0
	br bool %tmp.6.i, label %endif.1, label %then.1

then.1:
	store %std.class* %glb.class.IndexError.object, %std.class** %std.last_exception.type
	unwind
endif.1:
	%tmp.19 = getelementptr %std.list.%(name)s* %l, int 0, uint 1
	%tmp.20 = load %(item)s** %tmp.19
	%tmp.22 = getelementptr %(item)s* %tmp.20, int %index_addr.0.0
	%tmp.23 = load %(item)s* %tmp.22
	ret %(item)s %tmp.23
}


internal void %std.setitem(%std.list.%(name)s* %l, int %index.1, %(item)s %value) {
entry:
	%tmp.1 = setlt int %index.1, 0
	%tmp.11 = getelementptr %std.list.%(name)s* %l, int 0, uint 1
	br bool %tmp.1, label %then, label %endif

then:
	%tmp.4 = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	%tmp.121 = load %(item)s** %tmp.11
	%tmp.142 = getelementptr %(item)s* %tmp.121, int %tmp.9
	store %(item)s %value, %(item)s* %tmp.142
	ret void

endif:
	%tmp.12 = load %(item)s** %tmp.11
	%tmp.14 = getelementptr %(item)s* %tmp.12, int %index.1
	store %(item)s %value, %(item)s* %tmp.14
	ret void
}

internal void %std.setitem.exc(%std.list.%(name)s* %l, int %index.1, %(item)s %value) {
entry:
	%tmp.1 = setlt int %index.1, 0
	br bool %tmp.1, label %then.0, label %endif.0.i

then.0:
	%tmp.4 = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	%tmp.1.i5 = setlt int %tmp.9, 0
	br bool %tmp.1.i5, label %then.1, label %endif.0.i

endif.0.i:
	%index_addr.0.0 = phi int [ %tmp.9, %then.0 ], [ %index.1, %entry ]
	%tmp.1.i.i = getelementptr %std.list.%(name)s* %l, int 0, uint 0
	%tmp.2.i.i = load uint* %tmp.1.i.i
	%tmp.3.i.i = cast uint %tmp.2.i.i to int
	%tmp.6.i = setgt int %tmp.3.i.i, %index_addr.0.0
	br bool %tmp.6.i, label %endif.1, label %then.1

then.1:
	store %std.class* %glb.class.IndexError.object, %std.class** %std.last_exception.type
	unwind
endif.1:
	%tmp.17 = getelementptr %std.list.%(name)s* %l, int 0, uint 1
	%tmp.18 = load %(item)s** %tmp.17
	%tmp.20 = getelementptr %(item)s* %tmp.18, int %index_addr.0.0
	store %(item)s %value, %(item)s* %tmp.20
	ret void
}

internal %std.list.%(name)s* %std.add(%std.list.%(name)s* %a, %std.list.%(name)s* %b) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.4 = load uint* %tmp.3
	%tmp.6 = getelementptr %std.list.%(name)s* %b, int 0, uint 0
	%tmp.7 = load uint* %tmp.6
	%tmp.8 = add uint %tmp.7, %tmp.4
	%tmp.10 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint %tmp.8, uint* %tmp.10
	%tmp.13 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.14 = malloc %(item)s, uint %tmp.8
	store %(item)s* %tmp.14, %(item)s** %tmp.13
	%tmp.19 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	%tmp.20 = load %(item)s** %tmp.19
	%tmp.2.i14 = seteq uint %tmp.4, 0
	br bool %tmp.2.i14, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.0 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %entry ]
	%tmp.7.i = getelementptr %(item)s* %tmp.14, uint %i.0.i.0
	%tmp.11.i = getelementptr %(item)s* %tmp.20, uint %i.0.i.0
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.0, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.4
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	%tmp.28 = getelementptr %std.list.%(name)s* %b, int 0, uint 1
	%tmp.29 = load %(item)s** %tmp.28
	%tmp.42 = sub uint %tmp.8, %tmp.4
	%tmp.2.i319 = seteq uint %tmp.8, %tmp.4
	br bool %tmp.2.i319, label %copy.entry9, label %no_exit.i4

no_exit.i4:
	%i.0.i2.0 = phi uint [ %tmp.14.i8, %no_exit.i4 ], [ 0, %copy.entry ]
	%tmp.37.sum = add uint %i.0.i2.0, %tmp.4
	%tmp.7.i5 = getelementptr %(item)s* %tmp.14, uint %tmp.37.sum
	%tmp.11.i6 = getelementptr %(item)s* %tmp.29, uint %i.0.i2.0
	%tmp.12.i7 = load %(item)s* %tmp.11.i6
	store %(item)s %tmp.12.i7, %(item)s* %tmp.7.i5
	%tmp.14.i8 = add uint %i.0.i2.0, 1
	%tmp.2.i3 = setlt uint %tmp.14.i8, %tmp.42
	br bool %tmp.2.i3, label %no_exit.i4, label %copy.entry9

copy.entry9:
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.mul(%std.list.%(name)s* %a, int %times) {
entry:
	%tmp.0 = malloc %std.list.%(name)s
	%tmp.3 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.4 = load uint* %tmp.3
	%tmp.6 = cast int %times to uint
	%tmp.7 = mul uint %tmp.4, %tmp.6
	%tmp.9 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 0
	store uint %tmp.7, uint* %tmp.9
	%tmp.12 = getelementptr %std.list.%(name)s* %tmp.0, int 0, uint 1
	%tmp.13 = malloc %(item)s, uint %tmp.7
	store %(item)s* %tmp.13, %(item)s** %tmp.12
	%tmp.194 = setgt int %times, 0
	br bool %tmp.194, label %no_exit.preheader, label %loopexit

no_exit.preheader:
	%tmp.22 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	br label %no_exit

no_exit:
	%indvar = phi uint [ 0, %no_exit.preheader ], [ %indvar.next10, %copy.entry ]
	%i.0.0 = cast uint %indvar to int
	%tmp.23 = load %(item)s** %tmp.22
	%tmp.26 = load %(item)s** %tmp.12
	%tmp.29 = load uint* %tmp.3
	%tmp.32 = mul uint %indvar, %tmp.29
	%tmp.2.i9 = seteq uint %tmp.29, 0
	br bool %tmp.2.i9, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.2 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %no_exit ]
	%tmp.34.sum = add uint %i.0.i.2, %tmp.32
	%tmp.7.i = getelementptr %(item)s* %tmp.26, uint %tmp.34.sum
	%tmp.11.i = getelementptr %(item)s* %tmp.23, uint %i.0.i.2
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.2, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.29
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	%tmp.39 = add int %i.0.0, 1
	%tmp.19 = setlt int %tmp.39, %times
	%indvar.next10 = add uint %indvar, 1
	br bool %tmp.19, label %no_exit, label %loopexit

loopexit:
	ret %std.list.%(name)s* %tmp.0
}

internal %std.list.%(name)s* %std.inplace_add(%std.list.%(name)s* %a, %std.list.%(name)s* %b) {
entry:
	%tmp.2 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.3 = load uint* %tmp.2
	%tmp.5 = getelementptr %std.list.%(name)s* %b, int 0, uint 0
	%tmp.6 = load uint* %tmp.5
	%tmp.7 = add uint %tmp.6, %tmp.3
	%tmp.0 = malloc %(item)s, uint %tmp.7
	%tmp.11 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	%tmp.12 = load %(item)s** %tmp.11
	%tmp.2.i14 = seteq uint %tmp.3, 0
	br bool %tmp.2.i14, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.0 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %entry ]
	%tmp.7.i = getelementptr %(item)s* %tmp.0, uint %i.0.i.0
	%tmp.11.i = getelementptr %(item)s* %tmp.12, uint %i.0.i.0
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.0, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.3
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	%tmp.18 = getelementptr %std.list.%(name)s* %b, int 0, uint 1
	%tmp.19 = load %(item)s** %tmp.18
	%tmp.2.i319 = seteq uint %tmp.6, 0
	br bool %tmp.2.i319, label %copy.entry9, label %no_exit.i4

no_exit.i4:
	%i.0.i2.0 = phi uint [ %tmp.14.i8, %no_exit.i4 ], [ 0, %copy.entry ]
	%tmp.25.sum = add uint %i.0.i2.0, %tmp.3
	%tmp.7.i5 = getelementptr %(item)s* %tmp.0, uint %tmp.25.sum
	%tmp.11.i6 = getelementptr %(item)s* %tmp.19, uint %i.0.i2.0
	%tmp.12.i7 = load %(item)s* %tmp.11.i6
	store %(item)s %tmp.12.i7, %(item)s* %tmp.7.i5
	%tmp.14.i8 = add uint %i.0.i2.0, 1
	%tmp.2.i3 = setlt uint %tmp.14.i8, %tmp.6
	br bool %tmp.2.i3, label %no_exit.i4, label %copy.entry9

copy.entry9:
	store uint %tmp.7, uint* %tmp.2
	free %(item)s* %tmp.12
	store %(item)s* %tmp.0, %(item)s** %tmp.11
	ret %std.list.%(name)s* %a
}

internal void %std.append(%std.list.%(name)s* %a, %(item)s %value) {
entry:
	%tmp.2 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.3 = load uint* %tmp.2
	%tmp.3-off = add uint %tmp.3, 1
	%tmp.0 = malloc %(item)s, uint %tmp.3-off
	%tmp.12 = getelementptr %(item)s* %tmp.0, uint %tmp.3
	store %(item)s %value, %(item)s* %tmp.12
	%tmp.15 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	%tmp.16 = load %(item)s** %tmp.15
	%tmp.2.i5 = seteq uint %tmp.3, 0
	br bool %tmp.2.i5, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.0 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %entry ]
	%tmp.7.i = getelementptr %(item)s* %tmp.0, uint %i.0.i.0
	%tmp.11.i = getelementptr %(item)s* %tmp.16, uint %i.0.i.0
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.0, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.3
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	store uint %tmp.3-off, uint* %tmp.2
	free %(item)s* %tmp.16
	store %(item)s* %tmp.0, %(item)s** %tmp.15
	ret void
}

internal %(item)s %std.pop(%std.list.%(name)s* %a, int %index.1) {
entry:
	%tmp.1 = setlt int %index.1, 0
	br bool %tmp.1, label %then, label %endif

then:
	%tmp.4 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	br label %endif

endif:
	%index_addr.0 = phi int [ %tmp.9, %then ], [ %index.1, %entry ]
	%tmp.11 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	%tmp.12 = load %(item)s** %tmp.11
	%tmp.14 = getelementptr %(item)s* %tmp.12, int %index_addr.0
	%tmp.15 = load %(item)s* %tmp.14
	%tmp.18 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.19 = load uint* %tmp.18
	%tmp.19-off = add uint %tmp.19, 1073741823
	%tmp.16 = malloc %(item)s, uint %tmp.19-off
	%tmp.28 = cast int %index_addr.0 to uint
	%tmp.2.i14 = seteq int %index_addr.0, 0
	br bool %tmp.2.i14, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.0 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %endif ]
	%tmp.7.i = getelementptr %(item)s* %tmp.16, uint %i.0.i.0
	%tmp.11.i = getelementptr %(item)s* %tmp.12, uint %i.0.i.0
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.0, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.28
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	%tmp.35.sum = add int %index_addr.0, 1
	%tmp.48 = add uint %tmp.19, 4294967295
	%tmp.49 = sub uint %tmp.48, %tmp.28
	%tmp.2.i319 = seteq uint %tmp.48, %tmp.28
	br bool %tmp.2.i319, label %copy.entry9, label %no_exit.i4

no_exit.i4:
	%i.0.i2.0 = phi uint [ %tmp.14.i8, %no_exit.i4 ], [ 0, %copy.entry ]
	%i.0.i2.020 = cast uint %i.0.i2.0 to int
	%tmp.42.sum = add int %i.0.i2.020, %index_addr.0
	%tmp.7.i5 = getelementptr %(item)s* %tmp.16, int %tmp.42.sum
	%tmp.37.sum = add int %i.0.i2.020, %tmp.35.sum
	%tmp.11.i6 = getelementptr %(item)s* %tmp.12, int %tmp.37.sum
	%tmp.12.i7 = load %(item)s* %tmp.11.i6
	store %(item)s %tmp.12.i7, %(item)s* %tmp.7.i5
	%tmp.14.i8 = add uint %i.0.i2.0, 1
	%tmp.2.i3 = setlt uint %tmp.14.i8, %tmp.49
	br bool %tmp.2.i3, label %no_exit.i4, label %copy.entry9

copy.entry9:
	store uint %tmp.48, uint* %tmp.18
	free %(item)s* %tmp.12
	store %(item)s* %tmp.16, %(item)s** %tmp.11
	ret %(item)s %tmp.15
}

internal %(item)s %std.pop.exc(%std.list.%(name)s* %a, int %index.1) {
entry:
	%tmp.1 = setlt int %index.1, 0
	br bool %tmp.1, label %then.0, label %endif.0.i

then.0:
	%tmp.4 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.5 = load uint* %tmp.4
	%tmp.5 = cast uint %tmp.5 to int
	%tmp.9 = add int %tmp.5, %index.1
	%tmp.1.i20 = setlt int %tmp.9, 0
	br bool %tmp.1.i20, label %then.1, label %endif.0.i

endif.0.i:
	%index_addr.0.0 = phi int [ %tmp.9, %then.0 ], [ %index.1, %entry ]
	%tmp.1.i.i = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.2.i.i = load uint* %tmp.1.i.i
	%tmp.3.i.i = cast uint %tmp.2.i.i to int
	%tmp.6.i = setgt int %tmp.3.i.i, %index_addr.0.0
	br bool %tmp.6.i, label %endif.1, label %then.1

then.1:
	store %std.class* %glb.class.IndexError.object, %std.class** %std.last_exception.type
	unwind
endif.1:
	%tmp.19 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	%tmp.20 = load %(item)s** %tmp.19
	%tmp.22 = getelementptr %(item)s* %tmp.20, int %index_addr.0.0
	%tmp.23 = load %(item)s* %tmp.22
	%tmp.27-off = add uint %tmp.2.i.i, 1073741823
	%tmp.24 = malloc %(item)s, uint %tmp.27-off
	%tmp.36 = cast int %index_addr.0.0 to uint
	%tmp.2.i526 = seteq int %index_addr.0.0, 0
	br bool %tmp.2.i526, label %copy.entry12, label %no_exit.i6

no_exit.i6:
	%i.0.i4.0 = phi uint [ %tmp.14.i10, %no_exit.i6 ], [ 0, %endif.1 ]
	%tmp.7.i7 = getelementptr %(item)s* %tmp.24, uint %i.0.i4.0
	%tmp.11.i8 = getelementptr %(item)s* %tmp.20, uint %i.0.i4.0
	%tmp.12.i9 = load %(item)s* %tmp.11.i8
	store %(item)s %tmp.12.i9, %(item)s* %tmp.7.i7
	%tmp.14.i10 = add uint %i.0.i4.0, 1
	%tmp.2.i5 = setlt uint %tmp.14.i10, %tmp.36
	br bool %tmp.2.i5, label %no_exit.i6, label %copy.entry12

copy.entry12:
	%tmp.43.sum = add int %index_addr.0.0, 1
	%tmp.56 = add uint %tmp.2.i.i, 4294967295
	%tmp.57 = sub uint %tmp.56, %tmp.36
	%tmp.2.i31 = seteq uint %tmp.56, %tmp.36
	br bool %tmp.2.i31, label %copy.entry, label %no_exit.i

no_exit.i:
	%i.0.i.0 = phi uint [ %tmp.14.i, %no_exit.i ], [ 0, %copy.entry12 ]
	%i.0.i.032 = cast uint %i.0.i.0 to int
	%tmp.50.sum = add int %i.0.i.032, %index_addr.0.0
	%tmp.7.i = getelementptr %(item)s* %tmp.24, int %tmp.50.sum
	%tmp.45.sum = add int %i.0.i.032, %tmp.43.sum
	%tmp.11.i = getelementptr %(item)s* %tmp.20, int %tmp.45.sum
	%tmp.12.i = load %(item)s* %tmp.11.i
	store %(item)s %tmp.12.i, %(item)s* %tmp.7.i
	%tmp.14.i = add uint %i.0.i.0, 1
	%tmp.2.i = setlt uint %tmp.14.i, %tmp.57
	br bool %tmp.2.i, label %no_exit.i, label %copy.entry

copy.entry:
	store uint %tmp.56, uint* %tmp.1.i.i
	free %(item)s* %tmp.20
	store %(item)s* %tmp.24, %(item)s** %tmp.19
	ret %(item)s %tmp.23
}

internal %(item)s %std.pop(%std.list.%(name)s* %a) {
entry:
	%tmp.3 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.4 = load uint* %tmp.3
	%tmp.4 = cast uint %tmp.4 to int
	%tmp.6 = add int %tmp.4, -1
	%tmp.0 = call %(item)s %std.pop( %std.list.%(name)s* %a, int %tmp.6 )
	ret %(item)s %tmp.0
}

internal void %std.reverse(%std.list.%(name)s* %a) {
entry:
	%tmp.1 = getelementptr %std.list.%(name)s* %a, int 0, uint 0
	%tmp.2 = load uint* %tmp.1
	%tmp.610 = seteq uint %tmp.2, 1
	br bool %tmp.610, label %return, label %no_exit.preheader

no_exit.preheader:
	%tmp.9 = getelementptr %std.list.%(name)s* %a, int 0, uint 1
	br label %no_exit

no_exit:
	%lo.0.0 = phi uint [ 0, %no_exit.preheader ], [ %tmp.36, %no_exit ]
	%tmp. = add uint %tmp.2, 4294967295
	%hi.0.0 = sub uint %tmp., %lo.0.0
	%tmp.10 = load %(item)s** %tmp.9
	%tmp.13 = getelementptr %(item)s* %tmp.10, uint %lo.0.0
	%tmp.14 = load %(item)s* %tmp.13
	%tmp.26 = getelementptr %(item)s* %tmp.10, uint %hi.0.0
	%tmp.27 = load %(item)s* %tmp.26
	store %(item)s %tmp.27, %(item)s* %tmp.13
	%tmp.30 = load %(item)s** %tmp.9
	%tmp.33 = getelementptr %(item)s* %tmp.30, uint %hi.0.0
	store %(item)s %tmp.14, %(item)s* %tmp.33
	%tmp.36 = add uint %lo.0.0, 1
	%hi.0 = add uint %hi.0.0, 4294967295
	%tmp.6 = setlt uint %tmp.36, %hi.0
	br bool %tmp.6, label %no_exit, label %return

return:
	ret void
}
