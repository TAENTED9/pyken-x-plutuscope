# transpile.py
from pathlib import Path
from validator_emitter import emit_aiken_from_source

# Source Python file
SRC_FILE = r"C:\Users\USER\Desktop\PyKen Validators\module 103\l0-mock-tx.py"

# Read source
src = Path(SRC_FILE).read_text(encoding="utf-8")

# Transpile
aiken_code = emit_aiken_from_source(src)

# Print for debugging
print(aiken_code)

# Output to .aiken file
aiken_file = Path(SRC_FILE).with_suffix(".ak")
aiken_file.write_text(aiken_code, encoding="utf-8")
print(f"Aiken code written to: {aiken_file}")