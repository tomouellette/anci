#!/usr/bin/env -S just --justfile

[group: 'dev']
install:
  #!/bin/bash
  source .venv/bin/activate
  uv pip install -e .
  deactivate

[group: 'dev']
test:
  #!/bin/bash
  source .venv/bin/activate
  uv run pytest -v
  deactivate
