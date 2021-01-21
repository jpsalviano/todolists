# Makefile

run:
	gunicorn todolists.app:app

venv:
	source .venv/bin/activate

auser:
	PYTHONPATH=. python ./todolists/scripts/add_verified_user.py

ttables:
	PYTHONPATH=. python ./todolists/scripts/truncate_tables.py

tests:
	PYTHONPATH=. pytest ./todolists/tests/