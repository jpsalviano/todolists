#Makefile

run:
	/home/joao/todolists/.venv/bin/gunicorn --reload todolists.app:app

add-user:
	PYTHONPATH=. /home/joao/todolists/.venv/bin/python3 ./todolists/scripts/add_verified_user.py

trunc-tables:
	PYTHONPATH=. /home/joao/todolists/.venv/bin/python3 ./todolists/scripts/truncate_tables.py

tests:
	PYTHONPATH=. /home/joao/todolists/.venv/bin/pytest todolists/tests/