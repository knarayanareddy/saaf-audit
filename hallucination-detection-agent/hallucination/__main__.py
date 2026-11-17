"""Entry point for ``python -m hallucination``.

Delegates to ``cli.main()`` so the CLI can also be invoked as
``python -m hallucination.cli`` or imported programmatically.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
