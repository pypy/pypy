	.type	main, @function
main:
	;; a minimal example showing what kind of code gcc
	;; can produce for main(): some local variable accesses
	;; are relative to %ebp, while others are relative to
	;; %esp, and the difference %ebp-%esp is not constant
	;; because of the 'andl' to align the stack
	pushl	%ebp
	movl	%esp, %ebp
	subl	$8, %esp
	andl	$-16, %esp
	movl	$globalptr1, -4(%ebp)
	movl	$globalptr2, (%esp)
	pushl	$0
	call	foobar
	;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | -4(%ebp), 4(%esp)}
	popl	%eax
#APP
	/* GCROOT -4(%ebp) */
	/* GCROOT (%esp) */
#NO_APP
	movl	%ebp, %esp
	popl	%ebp
	ret

	.size	main, .-main
