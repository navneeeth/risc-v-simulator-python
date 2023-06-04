## RISC-V Simulator for Single Stage and Five Stage in Python 

### This is the README file for a RISC-V simulator built with Python for the course Computing Systems Architecture in my M.S. in Computer Engineering degree at New York University for Fall 2022.

Here, we use the Python programming language and concepts of single-stage, five-stage processors and simulate them based on the inputs provided in Data Memory and Instruction Memory for certain ASM instructions based on the RISC-V's ISA. 

The input will be the dmem.txt and imem.txt files saved in the same folder.

After running the simulator, the standard output as shown in the directory named `std_output` contain the following files:
1. Five Stage Data Memory Result: FS_DMEMResult.txt
2. Five Stage Registers File Result: FS_RFResult.txt
3. Five Stage State Result: StateResult_FS.txt
4. Single Stage Data Memory Result: SS_DMEMResult.txt
5. Single Stage Registers File Result: SS_RFResult.txt
6. Single Stage State Result: StateResult_SS.txt

### Instructions

#### Run the cyclesim.py file with the following command after saving the dmem.txt and imem.txt files in the same directory:

```
python cyclesim.py
```

The output files will be stored in the same directory.