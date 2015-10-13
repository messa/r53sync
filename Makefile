
check: venv
	PYTHONDONTWRITEBYTECODE=1 venv/bin/py.test -v tests

venv: requirements.txt
	[ -d venv ] || pyvenv-3.4 venv
	venv/bin/pip install -U pip
	venv/bin/pip install -U -r requirements.txt
	venv/bin/pip install -e .
	touch venv

.PHONY: check
