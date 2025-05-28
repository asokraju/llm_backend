# LightRAG Modifications

This is a modified version of LightRAG (https://github.com/HKUDS/LightRAG) included directly in this repository.

## Modifications Made

### 1. Python 3.13 Compatibility
**File**: `lightrag/kg/networkx_impl.py`
- Removed graspologic dependency installation
- Graspologic is not compatible with Python 3.13 and is not actually used in the codebase

### 2. Ollama Integration Fix
**File**: `lightrag/llm/ollama.py`
- Minor adjustments for better compatibility

## Original Repository
- **Source**: https://github.com/HKUDS/LightRAG
- **License**: MIT (see LICENSE file)
- **Version**: Based on commit from May 2024

## Why Included
Rather than requiring users to clone and patch LightRAG separately, we include it directly with the necessary modifications for Python 3.13 compatibility. This ensures:
- Consistent environment across all installations
- No need to maintain separate patches
- Easier deployment and setup