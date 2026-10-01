# Shot list — replacing the mockup crops with real photography

Every image on the site is a named slot in `oats/content/images.json`, cut from the four
ChatGPT mockups in `art/`. After a shoot, drop the new files in `art/`, point each slot's
`src`/`box` at them, run `python -m oats images`, then `python -m oats.tools.og`.

Direction from the brand brief: macro, glossy, indecently good. Gloss, creaminess, crumb
texture, sticky sauces, individual fruit pieces, chocolate cracks, swirl movement. Shallow
depth of field. Photograph it like ice cream and premium dessert advertising, never like
oatmeal: no flat beige bowls, no wooden spoon + linen napkin, no granola clichés.
Food first, package second. Every image must answer "do I want to eat that?"

Minimum size = the largest the slot is displayed at, ×2 for high-density screens. Shoot
everything at full camera resolution; these are only floors.

## Hero bowls — one per flavor (`card-<slug>`, 7 shots)

| | |
|---|---|
| Ratio / min size | 4:3 · 1200 × 900 px |
| Where | Home hero (cycles), flavor morph, flavor grid cards, product page lead image, share image |
| Composition | Consistent across all seven: low wide bowl or clear jar on the flavor's identity colour, pouch standing to one side, thick creamy base, swirl still marbled (not mixed in), crunch piled high, a few of the flavor's ingredients around the bowl. Same camera angle and lens for all seven — the site crossfades between them to say "same bowl, different vibe". |
| Backgrounds | Vanilla warm cream · Strawberry pink · Blueberry lavender · Birthday Cake cream + confetti · Cookies & Cream warm grey · Brownie Fudge deep cocoa · Choco PB peanut tan (hex values in `products.json → theme.bg`). Flat, so the card background can match. |

## Macro textures — one per flavor (`macro-<slug>`, 7 shots)

| | |
|---|---|
| Ratio / min size | 1:1 · 800 × 800 px |
| Where | Product page story block and thumbnails, "Why toasted?" collage |
| Composition | Extreme close-up, edge to edge, no bowl rim: swirl ribboning through the base with crunch pieces on top. The ingredient the flavor is named for should be identifiable. |

## Pouches — one per flavor (`pouch-<slug>`, 7 shots)

| | |
|---|---|
| Ratio / min size | 1:2 portrait · 400 × 800 px |
| Where | Build-a-box picker, product page thumbnail |
| Composition | Front-on pack shot on a flat matching colour, slight shadow. Can be a render once packaging is final. |

## The system (`system-base`, `system-swirl`, `system-crunch`)

| | |
|---|---|
| Ratio / min size | ~5:6 · 400 × 480 px each, on the same cream |
| Where | Home "The System" tiles |
| Composition | The three components as objects: base pouch, a swirl sachet full of strawberry, a crunch packet of clusters. Same lighting, same surface. |

## The ritual (`ritual-1-base` … `ritual-5-crunch`, 5 shots)

| | |
|---|---|
| Ratio / min size | 4:5 · 900 × 1100 px, identical framing for all five |
| Where | Home and How-it-works scroll sequence (crossfaded in place) |
| Frames | 1 pouch + empty clear jar · 2 base and milk pouring in · 3 set, thick, pale pudding · 4 strawberry swirl being squeezed in, ribbon mid-air · 5 crunch clusters falling onto the finished jar. Locked-off camera and jar position so the frames align; the whole point is that only the contents change. |

## Big food interruption (`hero-bowl`)

| | |
|---|---|
| Ratio / min size | 16:9 or wider · 2400 × 1350 px |
| Where | Full-bleed section on the home page; the share image (og.jpg) |
| Composition | The most indecent bowl you can make. Spoon going in, strawberry swirl, crumbs everywhere, very shallow focus. No text in the image — the site adds "Big bowl energy". |

## After hours (`after-hours`)

| | |
|---|---|
| Ratio / min size | 9:10 · 900 × 1000 px |
| Where | Dark "For when you're toasted" section |
| Composition | Late-night: low warm light, the Choco Peanut Butter bowl, a pouch, maybe a lamp glow. Moody, not literal. No leaves, nothing cannabis — the vibe does the work. |

## The lineup (`lineup`)

| | |
|---|---|
| Ratio / min size | ~3:1 · 2600 × 850 px |
| Where | Full-width band on Our Story |
| Composition | All seven pouches in a row on a shelf, flavor colours reading left to right. |
