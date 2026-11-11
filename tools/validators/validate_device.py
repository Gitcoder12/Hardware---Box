"""Backward-compatible validator entry point."""
import sys
from pathlib import Path
from hardware_box.validation import validate_device
import json

def validate(data): return validate_device(data)
def main(argv=None):
 args=sys.argv[1:] if argv is None else argv
 if len(args)!=1: print('Usage: python -m tools.validators.validate_device <device.json>',file=sys.stderr); return 2
 try: data=json.loads(Path(args[0]).read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc: print(f'ERROR: {exc}',file=sys.stderr); return 2
 errors=validate(data)
 if errors:
  for e in errors: print('ERROR:',e)
  return 1
 print('VALID:',args[0]); return 0
if __name__=='__main__': raise SystemExit(main())
