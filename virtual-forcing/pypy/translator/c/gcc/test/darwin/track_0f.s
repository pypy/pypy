_pypy_debug_open:
	subl	$92, %esp
	movl	%ebx, 76(%esp)
	call	L161
"L00000000014$pb":
L161:
	popl	%ebx
	movl	%ebp, 88(%esp)
	movl	%esi, 80(%esp)
	movl	%edi, 84(%esp)
	leal	LC18-"L00000000014$pb"(%ebx), %eax
	movl	%eax, (%esp)
	call	L_getenv$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	testl	%eax, %eax
	movl	%eax, %ebp
	je	L147
	cmpb	$0, (%eax)
	jne	L158
L147:
	movl	_pypy_debug_file-"L00000000014$pb"(%ebx), %esi
	testl	%esi, %esi
	je	L159
L154:
	movb	$1, _debug_ready-"L00000000014$pb"(%ebx)
	movl	80(%esp), %esi
	movl	76(%esp), %ebx
	movl	84(%esp), %edi
	movl	88(%esp), %ebp
	addl	$92, %esp
	ret
	.align 4,0x90
L158:
	movl	$58, 4(%esp)
	movl	%eax, (%esp)
	call	L_strchr$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	testl	%eax, %eax
	movl	%eax, %edi
	je	L160
	movl	%eax, %esi
	subl	%ebp, %esi
	leal	1(%esi), %eax
	movl	%eax, (%esp)
	call	L_malloc$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	movl	%ebp, 4(%esp)
	leal	1(%edi), %ebp
	movl	%esi, 8(%esp)
	movl	%eax, _debug_prefix-"L00000000014$pb"(%ebx)
	movl	%eax, (%esp)
	call	L_memcpy$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	movl	_debug_prefix-"L00000000014$pb"(%ebx), %eax
	movb	$0, (%eax,%esi)
L152:
	leal	LC19-"L00000000014$pb"(%ebx), %eax
	movl	$2, %ecx
	cld
	movl	%ebp, %esi
	movl	%eax, %edi
	repz
	cmpsb
	mov	$0, %eax
	je	0f
	movzbl	-1(%esi), %eax
	movzbl	-1(%edi), %ecx
	subl	%ecx,%eax
0:
	testl	%eax, %eax
	je	L147
	leal	LC20-"L00000000014$pb"(%ebx), %eax
	movl	%eax, 4(%esp)
	movl	%ebp, (%esp)
	call	L_fopen$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	movl	%eax, _pypy_debug_file-"L00000000014$pb"(%ebx)
	jmp	L147
L160:
	movb	$1, _debug_profile-"L00000000014$pb"(%ebx)
	jmp	L152
	.align 4,0x90
L159:
	movl	L___sF$non_lazy_ptr-"L00000000014$pb"(%ebx), %eax
	movl	$2, (%esp)
	addl	$176, %eax
	movl	%eax, _pypy_debug_file-"L00000000014$pb"(%ebx)
	call	L_isatty$stub
        ;; expected {92(%esp) | 76(%esp), 80(%esp), 84(%esp), 88(%esp) | }
	testl	%eax, %eax
	je	L154
	leal	LC21-"L00000000014$pb"(%ebx), %eax
	movl	80(%esp), %esi
	movl	%eax, _debug_start_colors_1-"L00000000014$pb"(%ebx)
	leal	LC22-"L00000000014$pb"(%ebx), %eax
	movl	84(%esp), %edi
	movl	%eax, _debug_start_colors_2-"L00000000014$pb"(%ebx)
	leal	LC23-"L00000000014$pb"(%ebx), %eax
	movl	88(%esp), %ebp
	movl	%eax, _debug_stop_colors-"L00000000014$pb"(%ebx)
	movb	$1, _debug_ready-"L00000000014$pb"(%ebx)
	movl	76(%esp), %ebx
	addl	$92, %esp
	ret
	.align 4,0x90