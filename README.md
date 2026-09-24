# rawi-tafsir

Tafsir datasets for [Rawi](https://rawiapp.xyz), and the generator that packs
them into the `.rtb` bundles both apps ship offline.

**The CDN is no longer the delivery mechanism.** The apps do not fetch tafsir at
runtime; they read bundles built from this tree. A push here reaches no device
until the generator is re-run, a release tag is cut, and both apps ship a build.

## Structure

```
tafsir/{slug}/{surah}/{ayah}.json    source of truth — reviewable, diffable
editions.json                        the catalogue (one row per shipping edition)
tools/                               the generator, the reference reader, the tests
dist/                                generated: {slug}.rtb + manifest.json (gitignored)
```

Each source JSON file: `{ "text": "...", "ayah": N, "surah": N }`

## Building

```bash
python3 tools/build-bundles.py                        # dist/*.rtb + dist/manifest.json
RTB_REAL_TREE=1 python3 tools/tests/test_bundles.py   # full round-trip
```

Stdlib Python 3, no dependencies. Format spec:
`../rawi-brain/product/tafsir-bundle-format.md`.

## Adding an edition

1. Drop the tree at `tafsir/<slug>/<surah>/<ayah>.json`.
2. Add one row to `editions.json` — `id`, `slug`, `name`, `author`, `language`
   (code), `attribution`, `attribution_required`, `awaiting_scholarly_review`.
   A row with no tree fails the build; a tree with no row is not bundled and the
   generator says so.
3. Re-run the generator, cut a release tag, bump the pinned manifest hash in both
   apps.

No Swift, no Kotlin: the catalogue ships with the data.

## Tafsirs

| Slug | Name | Language | Source |
|------|------|----------|--------|
| en-tafisr-ibn-kathir | Ibn Kathir | English | spa5k/tafsir_api |
| en-tafsir-maarif-ul-quran | Ma'arif al-Qur'an | English | spa5k/tafsir_api |
| en-tazkirul-quran | Tazkirul Quran | English | spa5k/tafsir_api |
| ar-tafseer-al-saddi | Al-Sa'di | Arabic | spa5k/tafsir_api |
| ar-tafsir-ibn-kathir | Ibn Kathir | Arabic | spa5k/tafsir_api |
| ar-tafseer-al-qurtubi | Al-Qurtubi | Arabic | spa5k/tafsir_api |
| tr-al-mukhtasar | Al-Mukhtasar | Turkish | UNKNOWN — see git history |
| tr-elmalili-yazir | Elmalılı Hamdi Yazır | Turkish | UNKNOWN — see git history |
| fr-al-mukhtasar | Al-Mukhtasar | French | UNKNOWN — see git history |

**German is between editions.** `de-rassoul` (Ibn Rassoul / IB Verlag) was
dropped 2026-09-24 and has **no `editions.json` row**, so it is not bundled and
not shipped; the tree stays for provenance
(`tafsir/de-rassoul/PROVENANCE.md`). German ships as `de-mourad` (*Erläuterung
des Koran*, DIdI) once that extraction lands, gated behind the ADR-013 scholarly
review like any new edition.

## License

Tafsir texts are scholarly works in the public domain or used under fair use for educational purposes. The JSON structuring and the bundle format are provided by Rawi.

**Where a licence makes credit a condition of the permission, the format enforces
it rather than trusting a call site.** An edition sets `attribution_required` in
`editions.json`; the generator refuses to build it without an `attribution`, the
reader refuses to open such a bundle at all, and the reader returns text and
attribution as **one value**, so no read surface can render the text without
holding the credit. `de-rassoul` is why this exists — its licence permits
reproduction, reprinting and translation *only where the source is credited*
(`wenn dabei auf diese Quelle hingewiesen wird`). See
`tafsir/de-rassoul/PROVENANCE.md`.
