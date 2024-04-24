# HorseWords - horse text utilities
This library is for parsing, validating, and augmenting horse text data. It only
supports the [Fimfarchive](https://www.fimfiction.net/user/116950/Fimfarchive) right
now. The API is very unstable.

Installation:
```bash
pip install --upgrade git+https://github.com/synthbot-anon/horsewords-lib
```

Loading data:
```python
from horsewords import fimfarchive

# Unpacked fimfarchive directory
CACHE_PATH = '/bulk/data/fimfarchive/fimfarchive - Mar 1, 2024'
archive = fimfarchive.Fimfarchive(CACHE_PATH)
```

This repo's main purpose right now is to upload the data to huggingface. To do that:
1. Run the `update_cache.ipynb` notebook.
2. Then run the `export_data.ipynb` notebook.
