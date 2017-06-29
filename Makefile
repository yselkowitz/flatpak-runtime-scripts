all:
	@echo "Usage: make [update-modulemd|runtime-local]"

update-modulemd:
	flatpak-module create-modulemd \
		--template flatpak-runtime.in.yaml \
		--package-list flatpak-runtime-packages.yaml \
		--dependency-tree flatpak-runtime.dependencies \
		-o flatpak-runtime.yaml

runtime-local:
	flatpak-module create-flatpak --runtime --info flatpak.json --module 'flatpak-runtime:f26'
