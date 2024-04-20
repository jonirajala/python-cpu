.global _start

.section .text
_start:
    MOV R0, #5
    MOV R1, #5
    CMP R0, R1
    MOVEQ R2, #1          /* Set R2 to 1 if R0 equals R1 */
    MOVNE R2, #0          /* Set R2 to 0 if R0 does not equal R1 */
    
    /* Check result */
    CMP R2, #1
    BEQ success
    B error

success:
    MOV R0, #1            /* Indicate success */
    B exit

error:
    MOV R0, #0            /* Indicate failure */
    B exit

exit:
    SWI 0                 /* Exit */
