This git repository holds documentation, data and scripts related to
maintaining Fedora modules for the desktop and for Flatpak runtimes
for Fedora.

Fedora Desktop Modules Plan
===========================

The plan is to have the following modules, in addition to a large number
of application modules:

**X11-base** - (already exists, name is perhaps not ideal). Holds the
core graphics stack - X, wayland libraries, mesa.

**desktop-runtime** - this module corresponds roughly to
org.gnome.Platform/org.gnome.SDK, but possibly with the addition of
Qt and other libraries frequently used by Linux workstation users.

**desktop** - this module contains the core GNOME desktop, but not desktop
applications.

**flatpak-runtime** - this is a small module that depends on
desktop-runtime, and adds Flatpak-specific stuff, and in particular
has a `buildroot` profile that install macros for relocation to `/app`. If you
build-requires this module, your package will be relocated to `/app`. Build
time modules like `autotools` are also *required* by this module so that they
can be included into the SDK flatpaks, while they are only *buildrequired*
by the `desktop-runtime` module.

The dependency graph looks something like:

```
flatpak-runtime ┐
desktop ────────┤
                └ desktop-runtime ┐
                                  ├ X11-base
                                  └ fonts ───────┐
                                                 └ Platform
```

The`flatpak-runtime module will have profiles corresponding to different
generated runtimes:

**runtime-base**: `org.fedoraproject.BasePlatform`. This is a smaller
runtime corresponding to `org.freedesktop.Platform`, and should
contain packages that we think could be supported over multiple
years. (Possibly the name should be something like runtime-stable
instead, but stable is a loaded word.)

**sdk-base**: `org.fedoraproject.BaseSdk` - SDK corresponding to
`org.fedoraproject.BasePlatform`. The goal is that most
flatpak-builder manifests that build against `org.freedesktop.Sdk` can
be built against this instead, though can't be a formal promise,
because org.freedesktop.Platform contains some amount of stray
binaries and libraries that we need to eliminate. (It contains, for
example, a binary of the Python `idle` IDE that doesn't work. Pulling
`idle` into our runtime via `python2-tools` would pull in
`python2-tkinter` and `tk`.)

**runtime**: org.fedoraproject.Platform - the runtime that Fedora
Flatpaks uses, roughly corresponding to `org.gnome.Platform`. It may
contain less stable libraries than `org.fedoraproject.BasePlatform`.

**sdk**: the SDK corresponding to the ``org.fedoraproject.Platform`.
The goal is that most flatpak-builder manifests that build against
`org.gnome.Sdk` can be built against this instead.

Usage of this module
====================

*Prequisites*: you need to have the following "upstream" runtimes installed:

* `org.freedesktop.Platform/x86_64/1.6`
* `org.freedesktop.Sdk/x86_64/1.6`
* `org.gnome.platform/x86_64/3.26`
* `org.gnome.Sdk/x86_64/3.26`

These will be used as sources to resolve hypthetical package sets that we
can compare to the package sets of the desktop modules.

You also need `python3-jinja2 python3-dnf` and possibly a few other Python
packages installed.

*Report generation*: run `make`. The first run will download f27 data
into the user-specific DNF cache and also generate a big index of all files
in Fedora. Subsequent runs are faster. Then open `report.html` in your
browser.
