import os

OS = os.getenv("OS")
OS_VERSION = os.getenv("OS_VERSION")

if OS == "fedora":
    RELEASE = f'f{OS_VERSION}'
    ID_PREFIX = 'org.fedoraproject'
    # If this is True, then we'll use the "base" profiles (freedesktop-based) as the main profiles
    BASEONLY = False

    ALL_ARCHES = ["aarch64", "ppc64le", "x86_64"]

    REPO_ARGS = ["--tag", f"f{OS_VERSION}-flatpak-runtime-packages"]
    SDK_EXTRA_REPO_ARGS = []

elif OS == "centos-stream" or OS == "rhel":
    if OS == "centos-stream":
        ID_PREFIX = "org.centos.stream"
    else:
        ID_PREFIX = "com.redhat"

    RELEASE = f'el{OS_VERSION}'
    BASEONLY = True

    ALL_ARCHES = ["aarch64", "ppc64le", "s390x", "x86_64"]

    def c10s_repo(variant):
        return ("https://composes.stream.centos.org/"
                + f"stream-{OS_VERSION}/development/latest-CentOS-Stream/compose/{variant}/$basearch/os/")

    REPO_ARGS = sum([
        ["--repo", f"c{OS_VERSION}s-{variant}:{c10s_repo(variant)}"] for variant in ("BaseOS", "AppStream")
    ], [])

    SDK_EXTRA_REPO_ARGS = sum([
        ["--repo", f"c{OS_VERSION}s-{variant}:{c10s_repo(variant)}"] for variant in ("CRB",)
    ], [])