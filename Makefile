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

all:
	@echo "Targets:"
	@echo "  report: Generates report.html, and a candidate flatpak-runtime.new.yaml"
	@echo "  update: Generates the above files, then copies flatpak-runtime.new.yaml to flatpak-runtime.yaml"

report: report.html flatpak-runtime.new.yaml

update: report
	cp flatpak-runtime.new.yaml flatpak-runtime.yaml

report.html $(PROFILE_FILES): $(PACKAGE_LISTS) package-notes.txt tools/generate-report.py report-template.html
	./tools/generate-report.py

$(FILE_LISTS): tools/generate-files.sh tools/list-files.py
	./tools/generate-files.sh $@

$(PACKAGE_LISTS): tools/resolve-files.py $(FILE_LISTS)

	for f in $(patsubst %.packages,%.files,$(PACKAGE_LISTS)) ; do	\
		./tools/resolve-files.py $$f ;		\
	done

flatpak-runtime.new.yaml: $(PROFILE_FILES) flatpak-runtime.in.yaml tools/generate-modulemd.py
	./tools/generate-modulemd.py

clean:
	rm -f out/* report.html flatpak-runtime.new.yaml

.PHONY: all clean report update
