_pypy_g___mm_le_0_perform_call:
	subl	$12, %esp
	movl	%ebx, (%esp)
	movl	%esi, 4(%esp)
	movl	%edi, 8(%esp)
	call	L82
"L00000000004$pb":
L82:
	popl	%ebx
	movl	16(%esp), %edi
	movl	20(%esp), %esi
L79:
	movl	4(%edi), %eax
	movl	20(%eax), %ecx
	incl	%ecx
	movl	4(%esi), %eax
	movl	20(%eax), %edx
	movl	L_pypy_g_array_45$non_lazy_ptr-"L00000000004$pb"(%ebx), %eax
	addl	8(%eax,%ecx,4), %edx
	andl	$255, %edx
	movl	L_pypy_g_array_2193$non_lazy_ptr-"L00000000004$pb"(%ebx), %eax
	movl	8(%eax,%edx,4), %ecx
	movl	(%esp), %ebx
	movl	4(%esp), %esi
	movl	8(%esp), %edi
	addl	$12, %esp
	jmp	*%ecx
L80:
	nop
