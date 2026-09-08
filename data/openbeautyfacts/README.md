# Open Beauty Facts snapshot

`products.jsonl` is a small, normalized snapshot of real product records retrieved from the Open Beauty Facts API. It is intended for reproducible demonstrations, not as verified manufacturer documentation.

- Source: https://world.openbeautyfacts.org/
- API documentation: https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/scanning-cosmetics-pet-food-and-other-products/
- Database license: Open Database License (ODbL) 1.0
- Attribution: Open Beauty Facts contributors
- Generator: `scripts/download_openbeautyfacts.py`
- Each record retains its barcode, source page URL, retrieval timestamp, and source identifier.

Open Beauty Facts is crowdsourced. Fields may be incomplete or inaccurate, so the application assigns these records medium reliability. Product-specific claims should still be checked against manufacturer material before publication.

If this snapshot is redistributed as part of a derived database, comply with the ODbL attribution and share-alike requirements.

