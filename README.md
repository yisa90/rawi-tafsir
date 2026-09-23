# rawi-tafsir

Tafsir datasets for [Rawi](https://rawiapp.xyz) — served via jsdelivr CDN.

## Structure

```
tafsir/{slug}/{surah}/{ayah}.json
```

Each JSON file: `{ "text": "...", "ayah": N, "surah": N }`

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
| de-rassoul | Tafsīr Al-Qurʾān Al-Karīm | German | Ibn Rassoul / IB Verlag — **attribution required**, see `tafsir/de-rassoul/PROVENANCE.md` |

## License

Tafsir texts are scholarly works in the public domain or used under fair use for educational purposes. The JSON structuring and CDN hosting is provided by Rawi.

**`de-rassoul` is different and the difference is binding.** Its licence permits
reproduction, reprinting and translation *only where the source is credited*
(`wenn dabei auf diese Quelle hingewiesen wird`). Attribution is a condition of
the permission, not a courtesy: any surface that renders this edition must also
render its source. See `tafsir/de-rassoul/PROVENANCE.md`, and note that both
apps carry the attribution string in their tafsir catalogue with a test that
fails if it goes missing.
