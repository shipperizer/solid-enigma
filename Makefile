.PHONY: server install migrate test

server: migrate
	nameko run --config config.yml blackjack

shell:
	nameko shell --config config.yml

install:
	pip install -r requirements.txt

migrate:
	alembic upgrade head

test:
	py.test test_blackjack.py
