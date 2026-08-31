.PHONY: nut nut-local clean test

nut:
	./scripts/build.sh nut

nut-local:
	./scripts/build.sh nut --local-overrides

test:
	python3 -m unittest discover -s tests -v
	python3 -m compileall -q scripts tests

lint:
	ruff check .

clean:
	rm -rf .build dist
