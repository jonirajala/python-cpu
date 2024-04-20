


import subprocess
import os

if __name__ == "__main__":
    for filename in os.listdir('tests/'):
        if not filename.endswith(".s"):
            continue
        filename = filename.replace(".s", "")
        s = subprocess.getstatusoutput(f'arm-none-eabi-as -o tests/{filename}.o tests/{filename}.s')
        print(s)
        s = subprocess.getstatusoutput(f'arm-none-eabi-ld -o tests/{filename}.elf tests/{filename}.o')
        print(s)