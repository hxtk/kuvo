# Kuvo

Kovu builds reproducible OCI images for Python projects. Inspired by the [Ko]
project from the Go ecosystem and the [uv] project from the Python ecosystem,
this project uses `uv` to create a reproducible Python installation and virtual
environment synchronized with the project's Lockfile.

[Ko]: https://ko.build/
[uv]: https://docs.astral.sh/uv/

## Configuration

Configure Kovu as a tool in your `pyproject.toml`. Kovu supports settings for
a base image, build path, entrypoint, command, repositories, and tags.

The entries in the `repositories` and `tags` lists both have Python f-string
semantics and can refer to any value in your `pyproject.toml`'s `[project]`
section.

The following shows the default configuration settings:

```toml
[tool.kuvo]
oci-path = "build/oci"
repositories = ["{name}"]
tags = ["latest", "v{version}"]
arch = "amd64"
os = "linux"
```

The omitted keys `entrypoint` and `cmd` default to `null`, which means the
images created inherit those values from the base image, if it had one.

This configuration produces an OCI layout directory in `build/oci` with the
final image, and pushes it to the repository `{name}`, which this project
resolves to `kuvo`. You can't use this default, since it contains no registry
name, and push commands fail as a result until you set a real name, but you
may load it with, for example, `podman pull oci:build/oci`. If your configuration
specifies more than one tag, you must choose one to pull into podman using
`podman pull oci:build/oci:<repository>:<tag>`.

You may inspect your configuration, rendered into its final form with all
substitutions, with `kuvo show-config`:

```sh
❯ uv run kuvo show-config
Config(oci_path='build/oci',
       base='cgr.dev/chainguard/glibc-dynamic:latest',
       entrypoint=None,
       cmd=['kuvo'],
       repositories=['ghcr.io/hxtk/kuvo'],
       tags=['latest', 'v0.1.0'],
       arch='amd64',
       os='linux')
```
