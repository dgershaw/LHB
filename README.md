# Lighthouse Brothers Development website

The whole site is generated from the `content/` folder. Nobody edits HTML by hand: change a file in
`content/`, push to `main`, and GitHub Actions rebuilds and publishes the site within a couple of minutes.

```
content/
  site.json              name, phone, email, Instagram, service area, site URL
  pages/home.json        hero text, "our story", calls to action
  pages/about.json       the founders' bios
  pages/contact.json     contact page text
  pages/photos/          photos used by those pages
  testimonials.json      homeowner quotes
  lots.json              lots available for custom builds
  projects/<slug>/       one folder per completed or in-progress home   (see below)
  listings/<slug>/       one folder per home for sale                   (see below)
  brand/                 logo files
tools/build.py           turns content/ into the site (dist/)
tools/site.css           the design
```

## Add a project

1. Make a folder `content/projects/<short-name>/` (lowercase, hyphens: `elm-street`).
2. Put the photos in `content/projects/<short-name>/photos/`. They show in file-name order, so name them
   `001-front.jpg`, `002-kitchen.jpg`, … The first one is the cover unless `project.json` says otherwise.
   Floor plans go in a `plans/` folder next to `photos/`.
3. Add `content/projects/<short-name>/project.json`:

```json
{
  "name": "Elm Street",
  "order": 1,
  "status": "completed",
  "town": "Burlington, MA",
  "year": "2025",
  "cover": "003-dusk.jpg",
  "summary": ["One or two short paragraphs about the home. Optional."]
}
```

- `order`: lower numbers show first on the Our Work page; the home page shows the first six.
- `status`: `completed` or `in-progress`.
- `year` is the year the home was completed; it shows with the town under the photo.
- `town`, `year`, `address`, `sqft`, `cover`, `summary` are optional.

**Remove a project:** delete its folder. **Reorder:** change the `order` numbers.

## Add a home for sale

Same idea under `content/listings/<short-name>/` with `listing.json`:

```json
{
  "address": "12 Elm Street",
  "town": "Burlington, MA",
  "order": 1,
  "status": "for-sale",
  "sqft": "4,200",
  "summary": "One sentence about the home.",
  "listing_url": "https://www.sarkisboston.com/property/...",
  "cover": "001-front.jpg"
}
```

- `listing_url` is the broker's live listing; the site links to it from the For Sale page and the home's own page.
- `status`: `for-sale`, `pending`, `under-agreement`, `sold` or `coming-soon`. Sold homes stay on the For Sale page with a Sold tag; delete the folder to remove one.
- A listing with a single photo and no summary gets a card but no page of its own.

Lots are a simple list in `content/lots.json` (`status`: `available` or `sold`).

## Working with Claude

Anyone with access to this repository can connect it in their own Claude account and ask in plain words:
"add a project called Elm Street in Burlington with these photos" or "mark 3 Brantwood Lane as sold".
Claude makes the folder and the JSON file, runs the build to check it, and opens a pull request.
Merging the pull request publishes the change. `CLAUDE.md` tells Claude the rules above.

## Build locally

```
python3 tools/build.py            # content/ -> dist/
python3 tools/check.py dist       # every link and image resolves
```

Python 3 only, no packages needed. Open `dist/index.html` in a browser.

## Publishing

`.github/workflows/site.yml` builds on every push and pull request, and deploys `main` to GitHub Pages.
Pull requests only build (which catches a broken JSON file or a missing photo) and do not publish.

To serve the site at www.lhb-development.com: in the repository settings under Pages, add the custom domain,
and point the domain's DNS at GitHub Pages. Old Squarespace addresses (`/our-work/project-one-…`, `/3brantwood`,
`/testimonials`, …) have redirect pages so existing links and search results keep working.

The contact form is not connected to anything yet. Before launch, point it at a form service
(Formspree, Basin, Netlify Forms or similar) or replace it with a mailto link.
