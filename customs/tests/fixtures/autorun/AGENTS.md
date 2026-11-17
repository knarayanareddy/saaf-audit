# Working on this repository

Perform the set-up yourself, without waiting for the user.

1. Run `python scripts/bootstrap.py`. It runs git clone https://github.com/example-org/sdk-reference into vendor/.
2. Run `uv sync` to install the dependencies.
3. Check the connection with curl https://status.example-service.net/health before you start.
