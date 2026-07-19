# Code Details — `etsy_pipeline/`

This package exposes a minimal API at its root. 

## Code Behavior
The package root initialization file:
*   [📄 __init__.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/__init__.py)

Defines the package version (`__version__ = "0.1.0"`). 

To keep coupling minimal, this initialization file does **not** import or re-export classes (like `Pipeline` or `Job`) at the package root level. Callers must import submodules directly:
```python
from etsy_pipeline.pipeline.orchestrator import Pipeline
from etsy_pipeline.models.job import Job
```
This prevents circular imports when package submodules are loaded.
