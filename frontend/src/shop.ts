// Shared storefront helpers (Problem 10).

/** Garment families, matching backend/recommend.py FAMILIES (checked in order). */
const FAMILY_RULES: [string, string][] = [
  ['quarter-zip', 'quarter-zip'],
  ['1/4', 'quarter-zip'],
  ['hood', 'hoodie'],
  ['t-shirt', 'tee'],
  ['tee', 'tee'],
  ['long-sleeve', 'tee'],
  ['long sleeve', 'tee'],
  ['crew', 'crewneck'],
  ['jacket', 'jacket'],
  ['fleece', 'jacket'],
  ['sweater', 'jacket'],
]

export function family(garmentType: string): string {
  const g = garmentType.toLowerCase()
  return FAMILY_RULES.find(([key]) => g.includes(key))?.[1] ?? 'other'
}

/** Shop categories: the nav Shop menu and the Home tiles. `cover` is a product whose photo represents it. */
export const CATEGORIES = [
  { key: 'hoodie', label: 'Hoodies', blurb: 'Game-day warmth', cover: 'basic-hoodie-big-yale' },
  { key: 'crewneck', label: 'Crewnecks', blurb: 'The campus classic', cover: 'champion-reverse-weave-crewneck' },
  { key: 'tee', label: 'Tees', blurb: 'Layer up or wear solo', cover: '2025-yale-vs-harvard-t-shirt' },
  { key: 'quarter-zip', label: 'Quarter-zips', blurb: 'Sharp enough for class', cover: 'branford-1-4-zip' },
  { key: 'jacket', label: 'Jackets & Fleece', blurb: 'For cold New Haven nights', cover: 'benjamin-franklin-fleece-jacket' },
] as const

/** Hand-picked best sellers for the Home "Top picks" row and the Shop menu sneak peeks. */
export const TOP_PICKS = [
  'district-vit-hoodie-vintage-bulldog',
  '2025-yale-vs-harvard-t-shirt',
  'champion-reverse-weave-crewneck',
  'branford-1-4-zip',
  'brooks-brothers-bomber-jacket-yale',
  'boola-boola-t-shirt',
  'basic-hoodie-big-yale',
  'district-vit-crewneck-vintage-standing-bulldog',
]

/** Open the chat widget from anywhere (e.g. the hero's "Ask the Stylist" button), optionally with a message. */
export function openStylist(message?: string) {
  window.dispatchEvent(new CustomEvent('open-stylist', { detail: { message } }))
}
