	.type	main, @function
main:
	;; this is an artificial example showing what kind of code gcc
	;; can produce for main()
	pushl	%ebp
	movl	%eax, $globalptr1
	movl	%esp, %ebp
	pushl	%edi
	subl	$8, %esp
	andl	$-16, %esp
	movl	%ebx, -8(%ebp)
	movl	8(%ebp), %edi
	call	foobar
	;; expected {4(%ebp) | -8(%ebp), %esi, -4(%ebp), (%ebp) | %edi}
.L1:
	cmpl	$0, %eax
	je	.L3
.L2:
	;; inlined function here with -fomit-frame-pointer
	movl	%eax, -12(%ebp)
	movl	%edi, %edx
	subl	$16, %esp
	movl	%eax, (%esp)
	movl	$42, %edi
	movl	%edx, 4(%esp)
	movl	%esi, %ebx
	movl	$nonsense, %esi
	call	foobar
	;; expected {4(%ebp) | -8(%ebp), %ebx, -4(%ebp), (%ebp) | -12(%ebp), 4(%esp)}
	addl	%edi, %eax
	movl	4(%esp), %eax
	movl	%ebx, %esi
	addl	$16, %esp
	movl	%eax, %edi
	movl	-12(%ebp), %eax
#APP
	/* GCROOT %eax */
#NO_APP
	;; end of inlined function
.L3:
	call	foobar
	;; expected {4(%ebp) | -8(%ebp), %esi, -4(%ebp), (%ebp) | %edi}
#APP
	/* GCROOT %edi */
#NO_APP
	movl	-8(%ebp), %ebx
	movl	-4(%ebp), %edi
	movl	%ebp, %esp
	popl	%ebp
	ret

	.size	main, .-main
