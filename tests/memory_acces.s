.global _start

.section .text
_start:
    MOV R0, #0x10       /* Assume this is a valid memory address */
    MOV R1, #12
    STR R1, [R0]          /* Store R1 at address R0 */
    LDR R2, [R0]          /* Load into R2 from address R0 */
    
    /* Verify memory operation */
    CMP R1, R2
    BNE error             /* If R1 not equal R2, branch to error */

success:
    MOV R0, #1            /* Indicate success */
    B exit

error:
    MOV R0, #0            /* Indicate failure */
    B exit

exit:
    SWI 0                 /* Exit */