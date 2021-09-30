This git repository holds the modulemd file and associated container files
for the Fedora Flatpak runtimes. It also holds scripts and data files used
to maintain and update the Fedora Flatpak runtimes.

Updating
========

*Prequisites*: you need to have the following "upstream" runtimes installed:

* `org.freedesktop.Platform/x86_64/21.08`
* `org.freedesktop.Sdk/x86_64/21.08`
* `org.gnome.Platform/x86_64/41`
* `org.gnome.Sdk/x86_64/41`

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
