"""How much of a document an agent actually read — and saying so.

Agents that reason over uploaded documents pass the FIRST N characters of each
one into their prompt. That is a defensible budget decision. Reporting it to the
auditor as "6 documents assessed" is not: a 40-page policy runs to roughly
80,000 characters, so a 4,000-character clip is the cover page and the table of
contents. The number looked like coverage and was really a file count.

Two things follow from being honest about it, and both are handled here:

1. The auditor sees what was read, not how many files existed.
2. The MODEL is told as well — which matters more than it sounds. An agent that
   does not know it is reading an extract will treat an absence as evidence of a
   gap, and that false gap is then proposed into the risk matrix. Told plainly
   that it holds an extract, it can say "not visible in the part I read" instead.

This is the seam retrieval will replace: when an agent starts selecting the
passages that matter instead of the first N characters, `DocCoverage` keeps its
shape and `chars_read` simply stops meaning "the beginning".
"""
from dataclasses import dataclass

from services.prompt_safety import safe_label


@dataclass(frozen=True)
class DocCoverage:
    """What one agent run actually took in from the uploaded documents."""
    documents: int          # documents handed to the agent
    documents_empty: int    # of those, the ones with no extracted text at all
    chars_read: int
    chars_total: int
    # Set once retrieval is doing the choosing: how many passages were selected,
    # and from how many distinct documents. With passages == 0 the text came off
    # the top of each file, and the wording below says so.
    passages: int = 0
    documents_hit: int = 0

    @property
    def percentage(self) -> int:
        if not self.chars_total:
            return 0
        return round(100 * self.chars_read / self.chars_total)

    @property
    def complete(self) -> bool:
        """True when nothing was left behind — then the wording can stay simple."""
        return self.chars_read >= self.chars_total

    def as_dict(self) -> dict:
        return {
            "documents": self.documents,
            "documents_empty": self.documents_empty,
            "chars_read": self.chars_read,
            "chars_total": self.chars_total,
            "percentage": self.percentage,
            "complete": self.complete,
            "passages": self.passages,
            "documents_hit": self.documents_hit,
            "sentence": self.sentence(),
        }

    def sentence(self) -> str:
        """One line the UI can show verbatim, and the run summary can log."""
        if self.documents == 0:
            return "no documents read"
        noun = "document" if self.documents == 1 else "documents"
        if self.complete:
            base = f"read {self.documents} {noun} in full"
        elif self.passages:
            # Retrieval chose these: say how many passages and from where, because
            # "the 18 most relevant passages" is a different and much better claim
            # than "the first 4,000 characters".
            hit = self.documents_hit or self.documents
            base = (f"read the {self.passages} most relevant passage"
                    f"{'' if self.passages == 1 else 's'} "
                    f"({self.chars_read:,} of {self.chars_total:,} characters, {self.percentage}%) "
                    f"from {hit} of {self.documents} {noun}")
        else:
            base = (f"read {self.chars_read:,} of {self.chars_total:,} characters "
                    f"across {self.documents} {noun} ({self.percentage}%)")
        if self.documents_empty:
            base += f" · {self.documents_empty} had no extractable text"
        return base


def clip_documents(items, limit: int) -> tuple[list[str], DocCoverage]:
    """Clip each (label, text) pair to `limit` characters, and measure the cost.

    Every clipped part carries its own marker, so the model can tell an extract
    from a whole document while it is reading — a per-document marker rather than
    one global caveat, because the model needs to know WHICH document it is only
    half-seeing when it decides whether a requirement is covered.
    """
    parts: list[str] = []
    documents = chars_read = chars_total = documents_empty = 0

    for label, text in items:
        documents += 1
        body = (text or "").strip()
        if not body:
            documents_empty += 1
            parts.append(f"DOCUMENT: {safe_label(label)}\n(no text could be extracted from this file)")
            continue
        chars_total += len(body)
        clipped = body[:limit]
        chars_read += len(clipped)
        header = f"DOCUMENT: {safe_label(label)}"
        if len(body) > limit:
            header += (f"\n[EXTRACT — you are reading the first {len(clipped):,} of {len(body):,} characters "
                       f"of this document. Anything not shown here is unknown to you, not absent: do not "
                       f"conclude something is missing because it does not appear below.]")
        parts.append(f"{header}\n{clipped}")

    return parts, DocCoverage(documents, documents_empty, chars_read, chars_total)
