PACKAGE_LISTS =					\
	out/freedesktop-Platform.packages	\
	out/freedesktop-Sdk.packages		\
	out/gnome-Platform.packages		\
	out/gnome-Sdk.packages

PROFILE_FILES =					\
	out/runtime.profile			\
	out/runtime-base.profile		\
	out/sdk.profile				\
	out/sdk-base.profile

FILE_LISTS = \
          $(patsubst %.packages,%.files,$(PACKAGE_LISTS))

all: report.html flatpak-runtime.yaml

report.html $(PROFILE_FILES): $(PACKAGE_LISTS) package-notes.txt generate-report.py report-template.html
	./generate-report.py

flatpak-runtime.yaml: $(PROFILE_FILES) flatpak-runtime.in.yaml generate-modulemd.py
	./generate-modulemd.py

$(FILE_LISTS): %.files: generate-files.sh list-files.py
	./generate-files.sh $@

%.packages: %.files resolve-files.py
	./resolve-files.py $<

clean:
	rm -f out/*

.PHONY: clean
