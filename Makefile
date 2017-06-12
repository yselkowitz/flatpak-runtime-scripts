all:
	@echo "Usage: make update-modulemd"

update-modulemd:
	flatpak-module create-modulemd \
		--template flatpak-runtime.in.yaml \
		--package-list flatpak-runtime-packages.yaml \
		--dependency-tree flatpak-runtime.dependencies \
		-o flatpak-runtime.yaml
