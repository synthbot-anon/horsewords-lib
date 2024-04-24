# HorseFM - horse audio utilities
This library is for parsing, validating, and augmenting horse audio data.

Installation:
```bash
pip install --upgrade git+https://github.com/synthbot-anon/horsefm-lib
```

Loading data:
```python
from horsefm.datasets import clipper_datasets

clipper_repo = '/path/to/Master File'
dialogue_dataset = clipper_datasets.mlp_dialogue_dataset(clipper_repo)
data = dialogue_dataset.pandas()
```