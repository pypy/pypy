

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

internal void %std.inplace_add(%std.list.%(name)s* %a, %std.list.%(name)s* %b) {
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
	ret void
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
