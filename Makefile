PACKAGE_LISTS =					\
	out/freedesktop-Platform.packages	\
	out/freedesktop-Sdk.packages		\
	out/gnome-Platform.packages		\
	out/gnome-Sdk.packages

FILE_LISTS = \
          $(patsubst %.packages,%.files,$(PACKAGE_LISTS))

all: report.html

report.html: $(PACKAGE_LISTS) generate-report.py report-template.html
	./generate-report.py

$(FILE_LISTS): %.files: generate-files.sh list-files.py
	./generate-files.sh $@

%.packages: %.files resolve-files.py
	./resolve-files.py $<

clean:
	rm -f out/*

.PHONY: clean
