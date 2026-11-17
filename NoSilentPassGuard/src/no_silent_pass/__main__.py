"""``python -m no_silent_pass demo`` works without installing the command."""
import sys

from .cli import main

sys.exit(main())
