# rawi-tafsir

Tafsir data for [Rawi](https://rawiapp.xyz), **and the generator that turns it
into the bundles the apps ship.**

## What this repo is, as of 2026-09-24

It was pure data: no code, no build, and **a push was a publish** — the apps read
`tafsir/<slug>/<surah>/<ayah>.json` straight off jsDelivr at a pinned commit.

That is no longer true, and the difference matters:

- **A push is not a publish.** The apps no longer fetch anything at runtime. They
  read `.rtb` bundles built from this tree and shipped inside the app binary.
  Editing a JSON file changes nothing on any device until the generator is re-run,
  a release tag is cut, and **both apps ship a new build**.
- **This repo has code.** `tools/` is the only implementation of the `.rtb`
  format. Changing it changes what both apps read.
- **This repo has a release artifact.** `dist/` is generated and gitignored; the
  built bundles live on the GitHub release tag `tafsir-bundle-v1`, and each app
  verifies their `sha256` against the manifest at build time and at load.

The format spec is `../rawi-brain/product/tafsir-bundle-format.md` (eng-lead owns
it, ADR-012). It is canonical; this file does not restate it.

## Load-bearing — do NOT "fix"

- **The slug `en-tafisr-ibn-kathir` is misspelled on purpose.** The corrected
  spelling **403s** on the CDN, and the slug is now also what a user's saved
  preference and both platforms' tests point at. It looks exactly like a typo.
  Leave it alone. A test asserts the misspelling survives.
- **`editions.json` is the catalogue.** It replaced two hand-written lists
  (Swift `TafsirCatalog.allIncludingUnreviewed`, Kotlin
  `TafsirInfo.ALL_INCLUDING_UNREVIEWED`) that had to match with nothing enforcing
  it. Do not re-add an edition list to either app.
- **`tools/rtb_format.py`'s `SURAH_AYAH_COUNTS` is pinned to
  `AYAH_ORDER_VERSION = "4498d920be9450ff"`** — the same digest `ayah_embeddings.bin`
  and `position_index.bin` are keyed to, and the same one rawi-ml, iOS and Android
  compute. Never bump the constant to make the table pass; fix the table.
- **`tools/tests/fixtures/` is a parity contract, not a Python test asset.** The
  iOS and Android reader tests assert the same `fixture-expectations.json`.
  Regenerating the fixture to make a test pass silently re-points two other
  platforms' suites.
- **`de-rassoul` is orphaned, not dead.** It has no `editions.json` row, so it is
  not bundled and not shipped. The founder dropped the edition 2026-09-24; the tree
  stays for provenance. German ships as `de-mourad` when pm-content lands that
  extraction.

## Working here

```bash
python3 tools/build-bundles.py                          # dist/*.rtb + dist/manifest.json
python3 tools/tests/test_bundles.py                     # fast, fixture only
RTB_REAL_TREE=1 python3 tools/tests/test_bundles.py     # + full round-trip, ~50s
python3 tools/tests/make_fixture.py                     # regenerate the golden fixture
```

Stdlib Python 3 only, no venv, no dependencies — on purpose, because this runs on
the founder's laptop and in CI.

Adding an edition: drop the tree under `tafsir/<slug>/`, add one row to
`editions.json`, re-run the generator, cut a release tag, bump the pinned manifest
hash in both apps. No Swift, no Kotlin.

## Rawi Brain

Cross-project product state lives in ../rawi-brain — start with its README; run
/brief there.
