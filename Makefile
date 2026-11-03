.PHONY: all clean list themes languages single-column double-column en it cover-letter cover-letters
export APPLICATION

all:
	./scripts/build.sh all
	python3 scripts/cover-letter.py build-all

cover-letter:
	python3 scripts/cover-letter.py build "$${APPLICATION:?Set APPLICATION=company-slug}"

cover-letters:
	python3 scripts/cover-letter.py build-all

clean:
	./scripts/build.sh clean

list:
	./scripts/build.sh list

themes:
	./scripts/build.sh list-themes

languages:
	./scripts/build.sh list-languages

single-column:
	./scripts/build.sh single-column all

double-column:
	./scripts/build.sh double-column all

en:
	./scripts/build.sh double-column en

it:
	./scripts/build.sh double-column it
