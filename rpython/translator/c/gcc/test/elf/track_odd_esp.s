	.type	pypy_g_copy_flags_from_bases, @function
pypy_g_copy_flags_from_bases:
.LFB188:
	.cfi_startproc
	pushl	%ebp
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	xorl	%edx, %edx
	pushl	%edi
	.cfi_def_cfa_offset 12
	.cfi_offset 7, -12
	pushl	%esi
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushl	%ebx
	.cfi_def_cfa_offset 20
	.cfi_offset 3, -20
	subl	$1, %esp
	.cfi_def_cfa_offset 21
	movl	21(%esp), %ebx
	movb	$0, (%esp)
	movl	16(%ebx), %ebp
	movl	4(%ebp), %edi
	.p2align 4,,7
	.p2align 3
.L572:
	cmpl	%edi, %edx
	jge	.L573
.L590:
.L574:
	addl	$1, %edx
	movl	4(%ebp,%edx,4), %ecx
	testl	%ecx, %ecx
	je	.L585
.L576:
	movl	4(%ecx), %esi
	movl	(%esi), %esi
	subl	$404, %esi
	cmpl	$10, %esi
	ja	.L585
.L577:
	cmpb	$0, 443(%ebx)
	movl	$1, %esi
	jne	.L578
.L579:
	movzbl	443(%ecx), %esi
.L578:
	cmpb	$0, 444(%ebx)
	movl	%esi, %eax
	movb	%al, 443(%ebx)
	movl	$1, %esi
	jne	.L580
.L581:
	movzbl	444(%ecx), %esi
.L580:
	cmpb	$0, 446(%ebx)
	movl	%esi, %eax
	movb	%al, 444(%ebx)
	movl	$1, %esi
	jne	.L582
.L583:
	movzbl	446(%ecx), %esi
.L582:
	movl	%esi, %eax
	cmpl	%edi, %edx
	movb	%al, 446(%ebx)
	jl	.L590
.L573:
	movl	25(%esp), %edx
	movzbl	(%esp), %eax
	movl	420(%edx), %edx
	movl	%edx, 420(%ebx)
	addl	$1, %esp
	.cfi_remember_state
	.cfi_def_cfa_offset 20
	popl	%ebx
	.cfi_restore 3
	.cfi_def_cfa_offset 16
	popl	%esi
	.cfi_restore 6
	.cfi_def_cfa_offset 12
	popl	%edi
	.cfi_restore 7
	.cfi_def_cfa_offset 8
	popl	%ebp
	.cfi_restore 5
	.cfi_def_cfa_offset 4
	ret
	.p2align 4,,7
	.p2align 3
.L585:
	.cfi_restore_state
	movb	$1, (%esp)
	jmp	.L572
	.cfi_endproc
.LFE188:
	.size	pypy_g_copy_flags_from_bases, .-pypy_g_copy_flags_from_bases
