	.type	pypy_g_clear_large_memory_chunk, @function
pypy_g_clear_large_memory_chunk:
.LFB41:
	.loc 2 1513 0
	pushl	%ebp
.LCFI87:
	movl	%esp, %ebp
.LCFI88:
	subl	$72, %esp
.LCFI89:
.L543:
	.loc 2 1521 0
	movl	$420, 8(%esp)
	movl	$0, 4(%esp)
	movl	$pypy_g_array_16, (%esp)
	call	open
        ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	movl	%eax, -12(%ebp)
	.loc 2 1522 0
	cmpl	$-1, -12(%ebp)
	setne	%al
	movb	%al, -21(%ebp)
	.loc 2 1523 0
	cmpb	$0, -21(%ebp)
	je	.L544
	.loc 2 1524 0
	movl	12(%ebp), %eax
	movl	%eax, -16(%ebp)
	.loc 2 1525 0
	movl	8(%ebp), %eax
	movl	%eax, -4(%ebp)
	.loc 2 1526 0
	jmp	.L545
.L544:
	.loc 2 1528 0
	movl	12(%ebp), %eax
	movl	%eax, -20(%ebp)
	.loc 2 1529 0
	movl	8(%ebp), %eax
	movl	%eax, -8(%ebp)
.L546:
	.loc 2 1533 0
	cmpl	$0, -20(%ebp)
	setg	%al
	movb	%al, -22(%ebp)
	.loc 2 1534 0
	cmpb	$0, -22(%ebp)
	je	.L542
.L549:
.L548:
	.loc 2 1544 0
	movl	-20(%ebp), %eax
	movl	%eax, 8(%esp)
	movl	$0, 4(%esp)
	movl	-8(%ebp), %eax
	movl	%eax, (%esp)
	call	memset
        ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	.loc 2 1545 0
	jmp	.L542
.L545:
	.loc 2 1548 0
	cmpl	$0, -16(%ebp)
	setg	%al
	movb	%al, -23(%ebp)
	.loc 2 1549 0
	cmpb	$0, -23(%ebp)
	je	.L552
	.loc 2 1550 0
	jmp	.L551
.L552:
	.loc 2 1555 0
	movl	-12(%ebp), %eax
	movl	%eax, (%esp)
	call	close
        ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	movl	%eax, -36(%ebp)
	.loc 2 1556 0
	movl	-16(%ebp), %eax
	movl	%eax, -20(%ebp)
	.loc 2 1557 0
	movl	-4(%ebp), %eax
	movl	%eax, -8(%ebp)
	.loc 2 1558 0
	jmp	.L546
.L551:
	.loc 2 1561 0
	cmpl	$536870912, -16(%ebp)
	setg	%al
	movb	%al, -24(%ebp)
	.loc 2 1562 0
	cmpb	$0, -24(%ebp)
	je	.L555
	.loc 2 1563 0
	movl	$536870912, -52(%ebp)
	.loc 2 1564 0
	jmp	.L554
.L555:
	.loc 2 1569 0
	movl	-16(%ebp), %eax
	movl	%eax, -44(%ebp)
	.loc 2 1570 0
	movl	-44(%ebp), %eax
	movl	%eax, -52(%ebp)
.L554:
	.loc 2 1574 0
	movl	-52(%ebp), %eax
	movl	%eax, 8(%esp)
	movl	-4(%ebp), %eax
	movl	%eax, 4(%esp)
	movl	-12(%ebp), %eax
	movl	%eax, (%esp)
	call	read
        ;; expected {4(%ebp) | %ebx, %esi, %edi, (%ebp) | }
	movl	%eax, -48(%ebp)
	.loc 2 1575 0
	movl	-48(%ebp), %eax
	movl	%eax, -32(%ebp)
	.loc 2 1576 0
	cmpl	$0, -32(%ebp)
	setle	%al
	movb	%al, -25(%ebp)
	.loc 2 1577 0
	cmpb	$0, -25(%ebp)
	je	.L557
	.loc 2 1578 0
	jmp	.L552
.L557:
	.loc 2 1583 0
	movl	-32(%ebp), %edx
	movl	-16(%ebp), %eax
	subl	%edx, %eax
	movl	%eax, -40(%ebp)
	.loc 2 1584 0
	movl	-32(%ebp), %eax
	addl	-4(%ebp), %eax
	movl	%eax, -56(%ebp)
	.loc 2 1585 0
	movl	-40(%ebp), %eax
	movl	%eax, -16(%ebp)
	.loc 2 1586 0
	movl	-56(%ebp), %eax
	movl	%eax, -4(%ebp)
	.loc 2 1587 0
	jmp	.L545
.L542:
	.loc 2 1588 0
	leave
	ret
.LFE41:
	.size	pypy_g_clear_large_memory_chunk, .-pypy_g_clear_large_memory_chunk
