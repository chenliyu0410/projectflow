"""Write the three fictional sample Word templates (meeting minutes, quote, work order) next to this script.

The same builder backs the 「加入三份範例樣板」 button, so the files here always match what the app adds.
Run: api/.venv/Scripts/python.exe deploy/demo-templates/make_samples.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'api'))
from app.services.doc_template_service import SAMPLES, sample_docx  # noqa: E402

for sample in SAMPLES:
    target = Path(__file__).with_name(f'{sample["name"]}範例.docx')
    target.write_bytes(sample_docx(sample))
    print(target.name)
