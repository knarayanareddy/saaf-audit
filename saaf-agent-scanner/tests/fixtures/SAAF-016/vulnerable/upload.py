import tempfile
from pathlib import Path


def combine_docs(files):
    chunks = []
    for f in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(f.getbuffer())   # uploaded evidence, never deleted
            path = Path(tmp.name)
        chunks.append(path.read_bytes())
    return chunks
