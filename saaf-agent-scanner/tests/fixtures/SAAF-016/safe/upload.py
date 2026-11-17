import tempfile
from pathlib import Path


def combine_docs(files):
    chunks = []
    with tempfile.TemporaryDirectory() as d:
        for f in files:
            path = Path(d) / "upload.pdf"
            path.write_bytes(bytes(f.getbuffer()))
            chunks.append(path.read_bytes())
    return chunks
