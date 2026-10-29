#!/usr/bin/env python3
"""Real screenshot regression: blocked old UI; readable outline/font controls."""
from pathlib import Path
from check_text_backplates import inspect
root=Path(__file__).resolve().parents[1]/'examples/text-backplates'
expected={'old.json':5,'fixed.json':0,'font.json':0}
for name,count in expected.items():
    result=inspect(root/name)
    actual=len(result['findings'])
    assert actual==count,(name,actual,count)
    print(name,actual,'expected',count)
