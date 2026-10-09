#!/usr/bin/env python3
"""Build the Lighthouse Brothers Development website from the content/ folder.

    python3 tools/build.py [content_dir] [output_dir] [--artifact] [--max-photos N] [--max-width PX]

Everything editable lives in content/ (see README.md). This script turns it into plain HTML
under the output folder (default dist/), copying the photos it uses into dist/images/, and
writes sitemap.xml, robots.txt and redirect stubs for the old Squarespace URLs.

--artifact     preview build for claude.ai: links point at index.html files and the home page
               is written without the <html>/<head>/<body> skeleton
--max-photos N cap each gallery at N photos (preview only; the live site shows every photo)
--max-width PX downscale copied JPEGs to PX wide (needs Pillow; preview only)
"""
import sys, os, json, html, shutil

args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = sys.argv[1:]
C = os.path.abspath(args[0] if len(args) > 0 else 'content')
OUT = os.path.abspath(args[1] if len(args) > 1 else 'dist')
ARTIFACT = '--artifact' in flags
MAX_PHOTOS = int(flags[flags.index('--max-photos') + 1]) if '--max-photos' in flags else None
MAX_WIDTH = int(flags[flags.index('--max-width') + 1]) if '--max-width' in flags else None
HERE = os.path.dirname(os.path.abspath(__file__))
e = html.escape
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp')


def fail(msg):
    sys.exit(f'build error: {msg}')


def load(rel, required=True):
    p = os.path.join(C, rel)
    if not os.path.exists(p):
        if required: fail(f'missing {rel}')
        return None
    try:
        return json.load(open(p, encoding='utf-8'))
    except json.JSONDecodeError as ex:
        fail(f'{rel} is not valid JSON: {ex}')


def photos_in(rel):
    """image files in a content folder, in file-name order"""
    d = os.path.join(C, rel)
    if not os.path.isdir(d): return []
    return sorted(f'{rel}/{f}' for f in os.listdir(d) if f.lower().endswith(IMG_EXT) and not f.startswith('.'))


SITE = load('site.json')
BASE = SITE.get('url', '').rstrip('/')
TESTIMONIALS = load('testimonials.json', required=False) or []
LOTS = load('lots.json', required=False) or []
HOME, ABOUT, CONTACT = load('pages/home.json'), load('pages/about.json'), load('pages/contact.json')


def entries(kind, info_file):
    out = []
    base = os.path.join(C, kind)
    if not os.path.isdir(base): return out
    for slug in sorted(os.listdir(base)):
        if slug.startswith('.') or not os.path.isdir(os.path.join(base, slug)): continue
        info = load(f'{kind}/{slug}/{info_file}')
        info['slug'] = slug
        info['photos'] = photos_in(f'{kind}/{slug}/photos')
        info['plans'] = photos_in(f'{kind}/{slug}/plans')
        if not info['photos']: fail(f'{kind}/{slug}/photos has no photos')
        cover = info.get('cover')
        info['cover'] = f'{kind}/{slug}/photos/{cover}' if cover else info['photos'][0]
        if info['cover'] not in info['photos']: fail(f"{kind}/{slug}: cover {cover!r} is not in photos/")
        out.append(info)
    out.sort(key=lambda i: (i.get('order', 999), i['slug']))
    return out


PROJECTS = entries('projects', 'project.json')
LISTINGS = entries('listings', 'listing.json')
for p in PROJECTS:
    if 'name' not in p: fail(f"projects/{p['slug']}/project.json needs a \"name\"")
for l in LISTINGS:
    if 'address' not in l: fail(f"listings/{l['slug']}/listing.json needs an \"address\"")

STATUS = {'completed': 'Completed', 'in-progress': 'In progress', 'for-sale': 'For sale', 'sold': 'Sold',
          'coming-soon': 'Coming soon', 'under-agreement': 'Under agreement', 'pending': 'Pending', 'available': 'Lot available'}


def label(s):
    return STATUS.get(s, s.replace('-', ' ').capitalize())


# ---------- urls ----------
# Pages are folders with an index.html, so the live site has URLs like /our-work/cresthaven/.
WORK, SALE, ABOUT_P, CONTACT_P = 'our-work/', 'for-sale/', 'about/', 'contact/'


def href(p, depth):
    """link from a page at this depth to the pretty path p ('' is the home page)"""
    r = '../' * depth
    if ARTIFACT:
        return r + (p + 'index.html' if p == '' or p.endswith('/') else p)
    return r + p if p else (r or './')


def absolute(p):
    return f'{BASE}/{p}'


# ---------- images ----------
COPIED = set()


def img(rel, depth):
    """copy a content image into the output and return its URL from a page at this depth"""
    src = os.path.join(C, rel)
    if not os.path.exists(src): fail(f'image not found: {rel}')
    dst = os.path.join(OUT, 'images', rel)
    if dst not in COPIED:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not (os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src)):
            if MAX_WIDTH and rel.lower().endswith(('.jpg', '.jpeg')):
                from PIL import Image
                im = Image.open(src)
                if im.width > MAX_WIDTH:
                    im = im.convert('RGB').resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
                    im.save(dst, quality=80, optimize=True, progressive=True)
                else:
                    shutil.copyfile(src, dst)
            else:
                shutil.copyfile(src, dst)
        COPIED.add(dst)
    return '../' * depth + 'images/' + rel


# ---------- shell ----------
FONTS = 'https://fonts.googleapis.com/css2?family=Libre+Caslon+Display&family=Hanken+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap'
NAV = [(WORK, 'Our Work', 'work'), (SALE, 'For Sale', 'sale'), (ABOUT_P, 'About', 'about'), (CONTACT_P, 'Contact', 'contact')]
SITEMAP = []

JS = r'''
(function(){
  var slides=document.querySelectorAll('.hero__slide');
  if(slides.length>1 && !matchMedia('(prefers-reduced-motion: reduce)').matches){
    var i=0;setInterval(function(){slides[i].classList.remove('is-on');i=(i+1)%slides.length;slides[i].classList.add('is-on');},6000);
  }
  var box=document.getElementById('lightbox');
  if(box){
    var imgs=[].slice.call(document.querySelectorAll('[data-full]')),cur=0,big=box.querySelector('img'),cap=box.querySelector('.lb__count');
    function show(n){cur=(n+imgs.length)%imgs.length;big.src=imgs[cur].getAttribute('data-full');big.alt=imgs[cur].querySelector('img').alt;cap.textContent=(cur+1)+' / '+imgs.length;}
    imgs.forEach(function(a,n){a.addEventListener('click',function(ev){ev.preventDefault();show(n);box.hidden=false;document.body.style.overflow='hidden';box.querySelector('.lb__close').focus();});});
    function close(){box.hidden=true;document.body.style.overflow='';imgs[cur].focus();}
    box.querySelector('.lb__close').onclick=close;
    box.querySelector('.lb__prev').onclick=function(){show(cur-1)};
    box.querySelector('.lb__next').onclick=function(){show(cur+1)};
    box.addEventListener('click',function(ev){if(ev.target===box)close();});
    document.addEventListener('keydown',function(ev){if(box.hidden)return;if(ev.key==='Escape')close();if(ev.key==='ArrowRight')show(cur+1);if(ev.key==='ArrowLeft')show(cur-1);});
  }
  var f=document.getElementById('inquiry');
  if(f){f.addEventListener('submit',function(ev){ev.preventDefault();document.getElementById('form-note').hidden=false;});}
})();
'''


def page(path, title, desc, body, active='', image=None, extra_head=''):
    """write a page at the pretty path ('' = home, 'about/', 'our-work/cresthaven/')"""
    depth = path.count('/')
    r = '../' * depth
    links = []
    for p, t, a in NAV:
        cur = ' aria-current="page"' if a == active else ''
        links.append(f'<a href="{href(p, depth)}"{cur}>{t}</a>')
    logo, logo_w = img('brand/logo.png', depth), img('brand/logo-white.png', depth)
    fav, touch = img('brand/favicon.png', depth), img('brand/apple-touch-icon.png', depth)
    og_image = absolute('images/' + (image or HOME['hero']['photos'][0]))
    canonical = absolute(path)
    SITEMAP.append(canonical)
    head = f'''<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(SITE['name'])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{e(og_image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="{fav}"><link rel="apple-touch-icon" href="{touch}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{r}site.css">{extra_head}'''
    content = f'''<header class="top">
  <a class="mark" href="{href('', depth)}" aria-label="{e(SITE['name'])}, home"><img class="logo" src="{logo}" alt="{e(SITE['short_name'])}" width="85" height="54"></a>
  <nav aria-label="Main">{''.join(links)}</nav>
</header>
<main>
{body}
</main>
<footer class="foot">
  <div class="foot__in">
    <div>
      <img class="foot__logo" src="{logo_w}" alt="{e(SITE['short_name'])}" width="101" height="64">
      <p class="foot__big">{e(SITE['footer_line'])}</p>
      <a class="btn btn--light" href="{href(CONTACT_P, depth)}">{e(SITE['footer_cta'])}</a>
    </div>
    <dl class="foot__meta">
      <div><dt>Email</dt><dd><a href="mailto:{e(SITE['email'])}">{e(SITE['email'])}</a></dd></div>
      <div><dt>Phone</dt><dd><a href="tel:{e(SITE['phone_link'])}">{e(SITE['phone'])}</a></dd></div>
      <div><dt>Area</dt><dd>{e(SITE['area'])}</dd></div>
      <div><dt>Follow</dt><dd><a href="{e(SITE['instagram'])}" target="_blank" rel="noopener">Instagram</a></dd></div>
    </dl>
  </div>
  <p class="foot__legal">&copy; 2026 {e(SITE['name'])}</p>
</footer>
<script>{JS}</script>
'''
    if ARTIFACT and path == '':
        doc = head + '\n' + content
    else:
        doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
               '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
               f'{head}\n</head>\n<body>\n{content}</body>\n</html>\n')
    full = os.path.join(OUT, path, 'index.html')
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(doc)


def redirect(old, new):
    """stub page at an old Squarespace URL that sends visitors (and search engines) to the new page"""
    if ARTIFACT: return
    target = absolute(new)
    full = os.path.join(OUT, old.strip('/'), 'index.html')
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
        f'<link rel="canonical" href="{e(target)}"><meta http-equiv="refresh" content="0; url={e(target)}">'
        f'<meta name="robots" content="noindex"></head><body><p>This page has moved to <a href="{e(target)}">{e(target)}</a>.</p></body></html>\n')


def gallery(items, depth, alt, total=None):
    cells = []
    for k, rel in enumerate(items):
        u = img(rel, depth)
        cells.append(f'<a class="g__cell" href="{u}" data-full="{u}"><img loading="lazy" src="{u}" alt="{e(alt)}, photo {k + 1}"></a>')
    note = ''
    if total and total > len(items):
        note = f'<p class="note">Showing {len(items)} of {total} photos in this preview. The live site shows them all.</p>'
    return f'''<div class="g">{''.join(cells)}</div>{note}
<div class="lb" id="lightbox" hidden role="dialog" aria-label="Photo viewer">
  <button class="lb__close" type="button" aria-label="Close">Close</button>
  <button class="lb__prev" type="button" aria-label="Previous photo">&larr;</button>
  <img src="" alt="">
  <button class="lb__next" type="button" aria-label="Next photo">&rarr;</button>
  <p class="lb__count"></p>
</div>'''


def specs(facts):
    return '<dl class="specs">' + ''.join(f'<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>' for a, b in facts) + '</dl>'


def paragraphs(ps):
    return ''.join(f'<p>{e(t)}</p>' for t in ps)


def gallery_items(info):
    items = [p for p in info['photos'] if p != info['cover']]
    total = len(items)
    if MAX_PHOTOS and len(items) > MAX_PHOTOS:
        items = items[:MAX_PHOTOS]
    return items, total


def project_card(p, depth):
    meta = ' · '.join(x for x in (p.get('town'), p.get('year')) if x) or label(p.get('status', 'completed'))
    return f'''<a class="card" href="{href(WORK + p['slug'] + '/', depth)}">
  <figure><img loading="lazy" src="{img(p['cover'], depth)}" alt="{e(p['name'])}"></figure>
  <div class="card__row"><h3>{e(p['name'])}</h3><span class="card__meta">{e(meta)}</span></div>
</a>'''


def has_detail(l):
    return len(l['photos']) > 1 or l.get('summary')


def listing_card(l, depth):
    detail = href(SALE + l['slug'] + '/', depth) if has_detail(l) else None
    title = f'<a href="{detail}">{e(l["address"])}</a>' if detail else e(l['address'])
    pic = f'<img loading="lazy" src="{img(l["cover"], depth)}" alt="{e(l["address"])}">'
    figure = f'<a href="{detail}">{pic}</a>' if detail else pic
    sq = f" &middot; {e(l['sqft'])} sq ft" if l.get('sqft') else ''
    links = []
    if l.get('listing_url'):
        links.append(f'<a class="more" href="{e(l["listing_url"])}" target="_blank" rel="noopener">Live listing &nearr;</a>')
    if detail:
        links.append(f'<a class="more more--quiet" href="{detail}">Photos &amp; plans &rarr;</a>')
    status = l.get('status', 'for-sale')
    pill = 'pill--live' if status == 'for-sale' else ('pill--sold' if status == 'sold' else '')
    return f'''<article class="listing">
  <figure>{figure}</figure>
  <div><span class="pill {pill}">{e(label(status))}</span><h3>{title}</h3><p class="listing__town">{e(l.get('town', ''))}{sq}</p>
  {f'<p>{e(l["summary"])}</p>' if l.get('summary') else ''}{f'<p class="listing__links">{" ".join(links)}</p>' if links else ''}</div>
</article>'''


# ---------- pages ----------
def build():
    os.makedirs(OUT, exist_ok=True)
    shutil.copyfile(os.path.join(HERE, 'site.css'), os.path.join(OUT, 'site.css'))

    # HOME
    h = HOME['hero']
    slides = []
    for k, rel in enumerate(h['photos']):
        attrs = ' class="hero__slide is-on" fetchpriority="high"' if k == 0 else ' class="hero__slide" loading="lazy"'
        slides.append(f'<img{attrs} src="{img(rel, 0)}" alt="">')
    s = HOME['story']
    facts = ''.join(f'<div><span class="facts__k">{e(f["label"])}</span><span class="facts__v">{e(f["value"])}</span></div>' for f in HOME.get('facts', []))
    featured = PROJECTS[:HOME.get('featured_projects', 6)]
    on_market = [l for l in LISTINGS if l.get('status') != 'sold']
    quotes = ''.join(f'<figure class="q"><blockquote>&ldquo;{e(t["quote"])}&rdquo;</blockquote><figcaption>{e(t["name"])}</figcaption></figure>' for t in TESTIMONIALS)
    cta = HOME['cta']
    body = f'''
<section class="hero">
  <div class="hero__media">{''.join(slides)}</div>
  <div class="hero__text">
    <p class="eyebrow">{e(h['eyebrow'])}</p>
    <h1>{e(h['headline'])}</h1>
    <p class="hero__lede">{e(h['lede'])}</p>
    <div class="hero__cta"><a class="btn btn--light" href="{href(WORK, 0)}">See our work</a><a class="link-light" href="{href(SALE, 0)}">Homes for sale &rarr;</a></div>
  </div>
</section>
{f'<section class="facts wrap" aria-label="At a glance">{facts}</section>' if facts else ''}
<section class="story wrap">
  <figure class="story__img"><img loading="lazy" src="{img(s['photo'], 0)}" alt="{e(s['caption'])}"><figcaption>{e(s['caption'])}</figcaption></figure>
  <div class="story__text">
    <p class="eyebrow">{e(s['eyebrow'])}</p>
    <h2>{e(s['heading'])}</h2>
    {paragraphs(s['paragraphs'])}
    <a class="btn" href="{href(ABOUT_P, 0)}">{e(s['button'])}</a>
  </div>
</section>
<section class="work wrap">
  <div class="sec-head"><div><p class="eyebrow">Selected work</p><h2>Homes we&rsquo;ve built</h2></div><a class="more" href="{href(WORK, 0)}">All {len(PROJECTS)} projects &rarr;</a></div>
  <div class="cards">{''.join(project_card(p, 0) for p in featured)}</div>
</section>
{f"""<section class="sale-band"><div class="wrap">
    <div class="sec-head"><div><p class="eyebrow">Available now</p><h2>Homes for sale</h2></div><a class="more more--light" href="{href(SALE, 0)}">Homes &amp; lots &rarr;</a></div>
    <div class="listings">{''.join(listing_card(l, 0) for l in on_market[:2])}</div>
</div></section>""" if on_market else ''}
{f'<section class="voices wrap" id="homeowners"><p class="eyebrow">From homeowners</p><div class="quotes">{quotes}</div></section>' if quotes else ''}
<section class="cta wrap">
  <h2>{e(cta['heading'])}</h2>
  <p>{e(cta['text'])}</p>
  <a class="btn" href="{href(CONTACT_P, 0)}">{e(cta['button'])}</a>
</section>'''
    ld = {"@context": "https://schema.org", "@type": "HomeAndConstructionBusiness", "name": SITE['name'],
          "alternateName": SITE['short_name'], "url": BASE + '/', "logo": absolute('images/brand/logo.png'),
          "image": absolute('images/' + h['photos'][0]), "description": SITE['description'],
          "telephone": SITE['phone_link'], "email": SITE['email'], "foundingDate": str(SITE.get('founded', '')),
          "areaServed": ["Burlington, MA", "Woburn, MA", "Greater Boston, MA"], "sameAs": [SITE['instagram']]}
    page('', f"{SITE['name']} | {SITE['tagline']}", SITE['description'], body,
         extra_head=f'\n<script type="application/ld+json">{json.dumps(ld)}</script>')
    redirect('/home', '')
    redirect('/testimonials', '#homeowners')

    # WORK INDEX
    body = f'''<section class="pagehead wrap"><p class="eyebrow">Our work</p><h1>Homes we&rsquo;ve built</h1>
<p class="lede">Every home blends classic architectural details with modern sensibilities, fits naturally into its neighborhood, and is crafted with care and determination.</p></section>
<section class="wrap"><div class="cards">{''.join(project_card(p, 1) for p in PROJECTS)}</div></section>'''
    page(WORK, f"Our Work | {SITE['name']}",
         f"Completed and in-progress homes by {SITE['name']} in Burlington, Woburn and the Boston area.", body, 'work',
         image=PROJECTS[0]['cover'] if PROJECTS else None)

    # PROJECT PAGES
    for k, p in enumerate(PROJECTS):
        prev, nxt = PROJECTS[k - 1], PROJECTS[(k + 1) % len(PROJECTS)]
        items, total = gallery_items(p)
        facts = []
        if p.get('address'): facts.append(('Address', p['address']))
        if p.get('town'): facts.append(('Town', p['town']))
        if p.get('year'): facts.append(('Completed', p['year']))
        if p.get('sqft'): facts.append(('Living area', p['sqft'] + ' sq ft'))
        if not p.get('year'): facts.append(('Status', label(p.get('status', 'completed'))))
        facts.append(('Photos', str(len(p['photos']))))
        plans = ''.join(f'<figure><img loading="lazy" src="{img(i, 2)}" alt="Floor plan, {e(p["name"])}"></figure>' for i in p['plans'])
        body = f'''<section class="phero"><img src="{img(p['cover'], 2)}" alt="{e(p['name'])}" fetchpriority="high"></section>
<section class="pinfo wrap"><div><p class="eyebrow"><a href="{href(WORK, 2)}">Our work</a></p><h1>{e(p['name'])}</h1>{paragraphs(p.get('summary', []))}</div>{specs(facts)}</section>
<section class="wrap">{gallery(items, 2, p['name'], total)}</section>
{f'<section class="wrap plans"><p class="eyebrow">Floor plans</p><div class="plans__grid">{plans}</div></section>' if plans else ''}
<nav class="pager wrap" aria-label="More projects"><a href="{href(WORK + prev['slug'] + '/', 2)}"><small>Previous</small>{e(prev['name'])}</a><a href="{href(WORK + nxt['slug'] + '/', 2)}"><small>Next</small>{e(nxt['name'])}</a></nav>'''
        where = f", {p['town']}" if p.get('town') else ''
        page(WORK + p['slug'] + '/', f"{p['name']} | {SITE['name']}",
             f"{p['name']}{where}: a home built by {SITE['name']}. {len(p['photos'])} photos.", body, 'work', image=p['cover'])
        for old in p.get('redirect_from', []):
            redirect(old, WORK + p['slug'] + '/')

    # FOR SALE
    rows = ''.join(f'<tr><td>{e(l["address"])}</td><td>{e(l.get("town", ""))}</td><td><span class="pill{" pill--sold" if l.get("status") == "sold" else ""}">{e(label(l.get("status", "available")))}</span></td></tr>' for l in LOTS)
    lots = f'''<section class="wrap lots"><div class="sec-head"><div><p class="eyebrow">Build on one of our lots</p><h2>Lots ready for a custom home</h2></div></div>
<div class="tablewrap"><table><thead><tr><th>Address</th><th>Town</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">Each lot can be customized to the buyer&rsquo;s preference. <a href="{href(CONTACT_P, 1)}">Ask us about a lot &rarr;</a></p></section>''' if LOTS else ''
    cards = '<div class="listings listings--page">' + ''.join(listing_card(l, 1) for l in LISTINGS) + '</div>' if LISTINGS else \
        f'<p class="lede">Nothing on the market right now. <a href="{href(CONTACT_P, 1)}">Get in touch</a> to hear about upcoming homes first.</p>'
    body = f'''<section class="pagehead wrap"><p class="eyebrow">For sale</p><h1>Homes and lots available</h1>
<p class="lede">Move into a finished LHB home, or choose a lot and we&rsquo;ll design and build to your preference.</p></section>
<section class="wrap">{cards}</section>
{lots}'''
    page(SALE, f"Homes for Sale | {SITE['name']}",
         'New LHB homes for sale in Burlington, MA, plus lots available for custom builds in Burlington and Woburn.', body, 'sale',
         image=LISTINGS[0]['cover'] if LISTINGS else None)

    # LISTING PAGES
    for l in LISTINGS:
        if not has_detail(l): continue
        items, total = gallery_items(l)
        facts = [('Town', l.get('town', '')), ('Status', label(l.get('status', 'for-sale')))]
        if l.get('sqft'): facts.append(('Living area', l['sqft'] + ' sq ft'))
        plans = ''.join(f'<figure><img loading="lazy" src="{img(i, 2)}" alt="Floor plan, {e(l["address"])}"></figure>' for i in l['plans'])
        button = f'<a class="btn" href="{e(l["listing_url"])}" target="_blank" rel="noopener">Live listing: pricing &amp; showings</a>' if l.get('listing_url') else ''
        body = f'''<section class="phero"><img src="{img(l['cover'], 2)}" alt="{e(l['address'])}" fetchpriority="high"></section>
<section class="pinfo wrap"><div><p class="eyebrow"><a href="{href(SALE, 2)}">For sale</a></p><h1>{e(l['address'])}</h1>{f'<p>{e(l["summary"])}</p>' if l.get('summary') else ''}{button}</div>{specs(facts)}</section>
<section class="wrap">{gallery(items, 2, l['address'], total)}</section>
{f'<section class="wrap plans"><p class="eyebrow">Floor plans</p><div class="plans__grid">{plans}</div></section>' if plans else ''}'''
        page(SALE + l['slug'] + '/', f"{l['address']}, {l.get('town', '')} | {SITE['name']}",
             f"{l['address']}, {l.get('town', '')}: a new home by {SITE['name']}. {l.get('summary', '')}".strip(), body, 'sale', image=l['cover'])
        for old in l.get('redirect_from', []):
            redirect(old, SALE + l['slug'] + '/')

    # ABOUT
    people = []
    for k, who in enumerate(ABOUT['people']):
        people.append(f'''<section class="founder{' founder--flip' if k % 2 else ''} wrap">
  <figure><img loading="lazy" src="{img(who['photo'], 1)}" alt="{e(who['name'])}"><figcaption>{e(who.get('caption', ''))}</figcaption></figure>
  <div><p class="eyebrow">{e(who.get('role', ''))}</p><h2>{e(who['name'])}</h2>{paragraphs(who['paragraphs'])}</div>
</section>''')
    cta = ABOUT['cta']
    body = f'''<section class="pagehead wrap"><p class="eyebrow">About</p><h1>{e(ABOUT['heading'])}</h1><p class="lede">{e(ABOUT['lede'])}</p></section>
{''.join(people)}
<section class="cta wrap"><h2>{e(cta['heading'])}</h2><p>{e(cta['text'])}</p><a class="btn" href="{href(CONTACT_P, 1)}">{e(cta['button'])}</a></section>'''
    names = ' and '.join(w['name'] for w in ABOUT['people'])
    page(ABOUT_P, f"About | {SITE['name']}", f"Meet {names}, the founders of {SITE['name']}.", body, 'about',
         image=HOME['story']['photo'])

    # CONTACT
    opts = ''.join(f'<option>{e(o)}</option>' for o in CONTACT.get('interests', []))
    body = f'''<section class="contact wrap">
  <div class="contact__text"><p class="eyebrow">Contact</p><h1>{e(CONTACT['heading'])}</h1>
  <p class="lede">{e(CONTACT['lede'])}</p>
  {specs([('Email', SITE['email']), ('Phone', SITE['phone']), ('Area', SITE['area'])]).replace('class="specs"', 'class="specs specs--contact"')}</div>
  <form class="form" id="inquiry" novalidate>
    <label for="f-name">Name</label><input id="f-name" name="name" autocomplete="name" required>
    <label for="f-email">Email</label><input id="f-email" name="email" type="email" autocomplete="email" required>
    <label for="f-phone">Phone <span>(optional)</span></label><input id="f-phone" name="phone" type="tel" autocomplete="tel">
    {f'<label for="f-interest">I&rsquo;m interested in</label><select id="f-interest" name="interest">{opts}</select>' if opts else ''}
    <label for="f-msg">Message</label><textarea id="f-msg" name="message" rows="5" required></textarea>
    <button class="btn" type="submit">Send message</button>
    <p class="form__note" id="form-note" hidden>This form isn&rsquo;t connected yet. Please email {e(SITE['email'])} or call {e(SITE['phone'])}.</p>
  </form>
</section>
<figure class="contact__img"><img loading="lazy" src="{img(CONTACT['photo'], 1)}" alt="Interior of an LHB home"></figure>'''
    page(CONTACT_P, f"Contact | {SITE['name']}",
         f"Contact {SITE['name']} about homes for sale, lots, and custom builds north of Boston.", body, 'contact',
         image=CONTACT['photo'])

    # SEO files
    if not ARTIFACT:
        urls = ''.join(f'  <url><loc>{e(u)}</loc></url>\n' for u in SITEMAP)
        open(os.path.join(OUT, 'sitemap.xml'), 'w').write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
        open(os.path.join(OUT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
        open(os.path.join(OUT, '.nojekyll'), 'w').write('')


build()
print(f'built {OUT}: {len(PROJECTS)} projects, {len(LISTINGS)} listings, {len(SITEMAP)} pages, {len(COPIED)} images')
