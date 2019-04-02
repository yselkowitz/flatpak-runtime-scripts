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
	@echo "  report: Generates HTML reports in reports/, and a candidate flatpak-runtime.new.yaml"
	@echo "  update: Generates the above files, then copies flatpak-runtime.new.yaml to flatpak-runtime.yaml"

report: reports/applications.json reports/application-packages.json reports/runtime.html flatpak-runtime.new.yaml

update: report
	cp flatpak-runtime.new.yaml flatpak-runtime.yaml

reports/runtime.html $(PROFILE_FILES): $(PACKAGE_LISTS) package-notes.txt tools/generate-runtime-report.py tools/util.py runtime-template.html
	./tools/generate-runtime-report.py

$(FILE_LISTS): tools/generate-files.sh tools/list-files.py
	./tools/generate-files.sh $@

$(PACKAGE_LISTS): tools/resolve-files.py $(FILE_LISTS)
	for f in $(patsubst %.packages,%.files,$(PACKAGE_LISTS)) ; do	\
		./tools/resolve-files.py $$f || exit 1;		\
	done

out/fedora-appstream.xml.gz: tools/download-fedora-appstream.sh
	./tools/download-fedora-appstream.sh

out/flathub-appstream.xml.gz: tools/download-flathub-appstream.sh
	./tools/download-flathub-appstream.sh

out/ratings.json: tools/download-reviews.sh
	./tools/download-reviews.sh

reports/applications.json reports/application-packages.json: tools/generate-app-reports.py out/fedora-appstream.xml.gz out/flathub-appstream.xml.gz out/ratings.json
	./tools/generate-app-reports.py

flatpak-runtime.new.yaml: $(PROFILE_FILES) flatpak-runtime.in.yaml flatpak-runtime-baseonly.in.yaml tools/generate-modulemd.py tools/util.py
	./tools/generate-modulemd.py

clean:
	rm -f out/* report.html flatpak-runtime.new.yaml

.PHONY: all clean report update
