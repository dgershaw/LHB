# Working in this repository

This is the website of Lighthouse Brothers Development (LHB), a home builder north of Boston. It is a
static site generated from `content/` by `tools/build.py`. The owners, David Gershaw and Shawn McSheffrey,
are not developers: they will ask for changes in plain language, usually about projects and homes for sale.

## Rules

- Edit `content/` only. Never hand-edit generated HTML; `dist/` is build output and is not committed.
- One folder per project (`content/projects/<slug>/`) and per listing (`content/listings/<slug>/`), each with
  its `project.json` / `listing.json` and a `photos/` folder (optional `plans/`). README.md documents every field.
- Slugs are lowercase with hyphens. Photos show in file-name order; prefix new photos with `001-`, `002-`, ….
  Keep uploaded photos at their original quality; the build does not resize them.
- To remove a project or listing, delete its folder. To reorder, change `order`.
- After any change run `python3 tools/build.py content dist && python3 tools/check.py dist` and fix what it reports.
- Make changes on a branch and open a pull request; merging to `main` publishes the site through GitHub Actions.
- Design changes go in `tools/site.css`; page structure in `tools/build.py`. Keep the site working at phone width,
  keep every image with alt text, and keep the per-page `<title>` and meta description.
- Do not add a build dependency beyond the Python standard library (Pillow is optional, used only for previews).
