This git repository holds the modulemd file and associated container files
for the Fedora Flatpak runtimes. It also holds scripts and data files used
to maintain and update the Fedora Flatpak runtimes.

Updating
========

*Prequisites*: you need to have the following "upstream" runtimes installed:

* `org.freedesktop.Platform/x86_64/22.08`
* `org.freedesktop.Sdk/x86_64/22.08`
* `org.gnome.Platform/x86_64/43`
* `org.gnome.Sdk/x86_64/43`

You also need `python3-jinja2` and possibly a few other Python
packages installed.

And finally, you'll need to have [fedmod](https://pagure.io/modularity/fedmod) installed.
You should run `fedmod fetch-metadata` initially and whenever you want to download
a fresh set of metadata from Fedora. `fedmod` never updates metadata on its own.

*How it works*: The files in the upstream runtimes are the primary source for the contents
of the corresponding Fedora runtimes. When you type `make update`, the
steps are as follows:

 * List the contents of selected directories of the upstream runtime
   (`tools/list-files.py`)
 * Exclude and rename files, and otherwise tweak the contents of the
   resulting lists, and find the Fedora packages that contain the
   corresponding packages. (`tools/resolve-files.py`)
 * Find all dependencies of the resolved packages using `fedmod resolve-deps`,
   correlate it all together, figure out the install profiles for each runtime,
   and create `report/runtime.html`. (`tools/generate-runtime-report.py`)
 * Create a `flatpak-runtime.new.yaml` using the profiles. (`tools/generate-modulemd.py`)
 * Finds data about applications packaged in Fedora and Flathub
   (`tools/download-fedora-appstream.sh`, `tools/download-flathub-appstream.sh`,
   `tools/download-reviews.py`)
 * Finds out how those applications would build using the *current* build of the
   runtime (not the one that we're creating here) , and generates more reports
   in `reports/`. (`tools/generate-app-reports.py`). (Improvement would be to use
   the candidate next build - requires us to pass the runtime data to fedmod rather
   than have fedmod download it from Koji.)
 * Copy `flatpak-runtime.new.yaml` to `flatpak-runtime.yaml`

*Report generation*: if you type `make report` instead then all the above happens
except the last step.

Tweaking the result
===================
The main way to tweak the result is to edit and extend the data embedded in
`tools/resolve-files.py`. Make sure you add comments explaining why you are
excluding files, and feed back exclusions to the upstream runtime maintainers
as appropriate.

Package notes
=============
To aid in keeping track of the status of all the packages in
`report.html`, notes and "flags" are read from package-notes.txt. The
notes are added to `report.html` and the flags affect formatting. The
top of that file has a comment describing the simple format.

Creating a runtime for a new Fedora release
===========================================
First make sure that the branches for new Fedora release are created in the
following components:

 * [modules/flatpak-runtime](https://src.fedoraproject.org/modules/flatpak-runtime/branches) - this repository
 * [modules/flatpak-common](https://src.fedoraproject.org/modules/flatpak-common/branches)
 * [module/flatpak-sdk](https://src.fedoraproject.org/modules/flatpak-sdk/branches)
 * [rpms/flatpak-runtime-config](https://src.fedoraproject.org/rpms/flatpak-runtime-config)

Once done, please do the following steps in this exact order:

 1. Update `rpms/flatpak-runtime-config` package for a new Fedora release - i.e. [f35](https://src.fedoraproject.org/rpms/flatpak-runtime-config/c/c070b580e4ed7b200bcd26e6e055c2a2848c4962) and [f36](https://src.fedoraproject.org/rpms/flatpak-runtime-config/c/41b65b28446c382c193b4e2ff6d330e7b0f0b26b)
 2. Create a new file under the data directory data/f36-live.packages (replace
    the f36 with the new release) and put the list of packages
    (`rpm -qa --qf "%{NAME}\n" | sort`) from a live Fedora Workstation media.
 3. Replace all occurrences of an old Fedora release with the new one in `modules/flatpak-runtime` - i.e. [f34 -> f35](https://src.fedoraproject.org/modules/flatpak-runtime/c/76972d6a76390f21e4e70fd960773e597d810de3) and [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-runtime/c/ff05f48642694c1aaf70df1fdc0a5a6d8fb30939)
 4. Bump the required freedesktop and GNOME Flatpak SDKs versions if required in
    `tools/generate-files.sh`
 5. Download the metadata for a new Fedora release with `fedmod  --dataset=f36
    fetch-metadata` (replace f36 with the new release). You might need to update
    the `/etc/fedmod/fedora.yaml` file and add a new release there. If the new
    Fedora is already released, then duplicate the f36 part under the `releases:`
    section [example](https://pagure.io/fork/tpopela/modularity/fedmod/c/0df9ced507b8e9ce76a62cc35015c403073873ca). If the new version isn't released yet, do the same, but replace
    `fedora-stable` with `fedora-branched`.
 6. Run `make new-runtime`. In case of any problems you will need to update the
    `tools/resolve-files.py` to adapt it for new library versions and so on.
    Once the new runtime files are generated, consult the content of it and again
    modify `tools/resolve-files.py` to exclude any libraries, binaries or packages
    if needed.
 7. Try to build the module and container locally with `flatpak-module local-build`
    to verify that the changes from previous step are working.
 8. Commit the change and do the official build with `fedpkg module-build -w`
    followed by `fedpkg flatpak-build`
 9. Update and build modules/flatpak-common - i.e. [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-common/c/17aeabbc448e3805a85e2c9313d40c608bc2611b?branch=f36)
     and do an official build of with with `fedpkg module-build -w`. If you will
     hit any build problems you might want to try to build the module locally
     against the local packages with `flatpak-module build-module`. For that you
     have to [setup your environment](https://docs.fedoraproject.org/en-US/flatpak/troubleshooting/#_rebuilding_a_module_against_a_local_component)
 10. Update modules/flatpak-sdk - i.e. [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-sdk/c/83742941dc2b7e5c0cad78cb25c3ed9cc1b17d1a?branch=f36)
     and build it with `fedpkg flatpak-build` (no need to build a module for
     flatpak-sdk). On the other hand if you will need to make any changes to the
     flatpak-runtime defitions (to add more packages that are not pulled on
     x86_64 - i.e. [this change](https://src.fedoraproject.org/modules/flatpak-runtime/c/4737e749c62b19daf07366444517be9b98ff7ac9?branch=f36))
     then you will need to again do a module build of flatpak-runtime and once
     it's done, you can start a new `fedpkg flatpak-build` of flatpak-runtime
     and flatpak-sdk.
 11. Create a bodhi update for the new runtime and SDK - i.e. https://bodhi.fedoraproject.org/updates/FEDORA-FLATPAK-2022-16d56b1bde
 12. Move all applications to the new runtime - i.e. [Evince Flatpak moving from f35 -> f36 ](https://src.fedoraproject.org/flatpaks/evince/c/7fccbf4bb8cea2d258226dfbe490327c59a44564?branch=stable)
     and build it with `fedpkg module-build -w` and `fedpkg flatpak-build`. Also
     it's a good time to update the `finish-args` from Flathub and update them
     in Fedora if needed. Also update the module packages with the changes from the new Fedora release - i.e. `fedmod rpm2flatpak --flatpak-common --force --flathub=gimp gimp`.
     You might find [the following howto useful](https://docs.fedoraproject.org/en-US/flatpak/tutorial/#_creating_application_yaml_and_container_yaml).
 13. Create bodhi updates for moved applications
 14. Switch to the new runtime for Anaconda - i.e. [f34 -> f35](https://pagure.io/pungi-fedora/c/d2e477b48368599834d6ec4adcc79f7115d98627?branch=main)
 15. Once everything is moved, deprecate the old runtime and SDK - TBD
