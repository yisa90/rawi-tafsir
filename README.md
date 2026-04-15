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
| tr-tafsir-ibn-kathir | Ibn Kathir | Turkish | QUL (resource 306) |

## License

Tafsir texts are scholarly works in the public domain or used under fair use for educational purposes. The JSON structuring and CDN hosting is provided by Rawi.
