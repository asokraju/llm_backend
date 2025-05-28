# LightRAG Patches

This directory contains patches for LightRAG to ensure compatibility with our system.

## Python 3.13 Compatibility Patch

**File**: `lightrag-python313-fix.patch`
**Purpose**: Removes graspologic dependency which doesn't support Python 3.13

### Applying the Patch

After cloning LightRAG, apply this patch:

```bash
cd LightRAG
git apply ../patches/lightrag-python313-fix.patch
```

### What the Patch Does

1. **Removes graspologic installation** from `lightrag/kg/networkx_impl.py`
   - Graspologic is not actually used in the codebase
   - It has compatibility issues with Python 3.13

2. **Minor fix** in `lightrag/llm/ollama.py`
   - Small adjustment for better compatibility

### Why This is Needed

Without this patch, you'll get:
```
ERROR: Package 'graspologic' requires a different Python: 3.13.2 not in '>=3.9,<3.13'
```

This patch ensures LightRAG works with Python 3.13.