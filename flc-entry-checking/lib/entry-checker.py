import inspect
import os
import sys

# Allow imports from parent directory.
curr_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
cda_tools_dir = os.path.dirname(os.path.dirname(curr_dir))
sys.path.insert(0, os.path.join(cda_tools_dir, 'cda-core\\lib'))

import competition # type: ignore

def main():
    comp = competition.Competition(input("Please enter full path of entry spreadsheet (with file extension): "))
    comp.check_entries()

if __name__ == "__main__":
    main()