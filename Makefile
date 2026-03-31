.PHONY: all clean list themes languages single-column double-column en it

all:
	./scripts/build.sh all

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
