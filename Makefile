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

report.html $(PROFILE_FILES): $(PACKAGE_LISTS) package-notes.txt tools/generate-report.py report-template.html
	./tools/generate-report.py

$(FILE_LISTS): tools/generate-files.sh tools/list-files.py
	./tools/generate-files.sh $@

$(PACKAGE_LISTS): tools/resolve-files.py $(FILE_LISTS)

	for f in $(patsubst %.packages,%.files,$(PACKAGE_LISTS)) ; do	\
		./tools/resolve-files.py $$f ;		\
	done

flatpak-runtime.yaml: $(PROFILE_FILES) flatpak-runtime.in.yaml tools/generate-modulemd.py
	./tools/generate-modulemd.py

clean:
	rm -f out/*

.PHONY: clean
