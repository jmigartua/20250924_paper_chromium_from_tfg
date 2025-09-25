

## Development

Install dev deps and run tests:

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Create a release (bumps version and updates CHANGELOG):

```bash
python scripts/release.py --bump patch --notes "Fixes and small improvements" --tag
```
