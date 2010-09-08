	.type	foobar, @function
foobar:
.LFB0:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	movq	%rsp, %rbp
	.cfi_offset 6, -16
	.cfi_def_cfa_register 6
	movl	%edi, -4(%rbp)
	cmpl	$4, -4(%rbp)
	ja	.L2
	mov	-4(%rbp), %eax
	movq	.L8(,%rax,8), %rax
	jmp	*%rax
	.section	.rodata
	.align 8
	.align 4
.L8:
	.quad	.L3
	.quad	.L4
	.quad	.L5
	.quad	.L6
	.quad	.L7
	.text
.L3:
	movl	$1, %eax
	jmp	.L9
.L4:
	movl	$12, %eax
	jmp	.L9
.L5:
	movl	$123, %eax
	jmp	.L9
.L6:
	movl	$1234, %eax
	jmp	.L9
.L7:
	movl	$12345, %eax
	jmp	.L9
.L2:
	movl	$42, %eax
.L9:
	leave
	ret
	.cfi_endproc
.LFE0:
	.size	foobar, .-foobar
