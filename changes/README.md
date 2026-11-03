# Unreleased changes

Each pull request adds one file here, and `CHANGELOG.md` is compiled from them at
release. Because every change is its own file, pull requests never collide on the
changelog. CI fails a pull request without one.

Name the file `+<slug>.<type>.md`, where the slug is anything unique and the type is
`added`, `changed`, `fixed` or `removed`:

```
changes/+vol-cone.added.md
```

The file holds one or two lines, written for someone using the package:

```markdown
`primitives.VolCone`: a cone from a frame, a height and a radius.
```

To use the issue number in the changelog, name the file `<issue>.<type>.md` instead.
A pull request with nothing for users to read, such as a typo fix, can take the
`no changelog` label.
