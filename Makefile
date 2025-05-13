# Makefile to remove __pycache__ directories and .dlo files

.PHONY: clean clean-py clean-dlo

# POSIX-friendly: works in WSL, MSYS2, Cygwin, or any shell that has `find`.
clean:
	@echo "Removing __pycache__ directories (POSIX)..."
	@find . -type d -name '__pycache__' -exec rm -rf {} +

# Cross-platform fallback that only requires Python in the PATH.
clean-py:
	@echo "Removing __pycache__ directories with Python (cross-platform)..."
	@python - <<'PY'
import shutil, pathlib, sys
for p in pathlib.Path('.').rglob('__pycache__'):
    try:
        shutil.rmtree(p)
        print(f'Removed {p}')
    except Exception as e:
        print(f'Failed to remove {p}: {e}', file=sys.stderr)
PY

# Remove all .dlo files
clean-dlo:
	@echo "Removing all .dlo files..."
	@find . -type f -name '*.dlo' -exec rm -f {} +
