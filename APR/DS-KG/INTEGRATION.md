# DS-KG Integration with Patch Generation

This document describes the integration between the DS-KG (Data Science Knowledge Graph) system and the patch generation module for automated program repair.

## Overview

The integration enables LLMs to fix broken code more accurately by providing relevant API documentation from the Knowledge Graph alongside error-marked code.

## Architecture

```
APRInput → PatchGenerator → GeneratedPatch (with error markers)
                                    ↓
DS-KG JSON files → DSKGEngine ← Error Signature Extraction
                        ↓
                  KG Query & Context Assembly
                        ↓
            build_repair_prompt (with KG context)
                        ↓
                  LLM Repair Prompt
```

## Components

### 1. DSKGEngine (`engine.py`)

**Purpose**: Load and query KG JSON files for API documentation.

**Key Classes**:
- `DSKGEntry`: TypedDict representing a single API entry
- `DSKGEngine`: Main query engine

**Key Methods**:
```python
engine = DSKGEngine(["kg_numpy.json", "kg_pandas.json"])

# Exact lookup
entry = engine.resolve_api_call("numpy", "array")

# Fuzzy search
entries = engine.get_by_name("array")

# Class methods (for AttributeError)
class_entry = engine.get_class_methods("pandas", "DataFrame")
```

**Data Structure**: Each entry contains:
- `name`: API name
- `path`: Full path (e.g., "numpy.array")
- `library`: Library name
- `parameters`: Required and optional parameters
- `returns`: Return type
- `description`: Short description
- `deprecated`: Boolean flag
- `alternatives`: List of alternatives (if deprecated)

### 2. KG Integration Module (`kg_integration.py`)

**Purpose**: Extract error signatures, query KG, and assemble context.

**Key Functions**:

#### `extract_error_signatures(apr_input, patch)`
Analyzes patch hunks and APRInput to extract structured error information:
- Error type (API_ERROR, UNDEFINED_NAME, RUNTIME_ERROR, etc.)
- API name
- Library name
- Scope context (for LOGIC_ERROR)

#### `query_kg_for_errors(kg_engine, signatures)`
Queries KG based on error signatures:
- **API_ERROR**: Direct lookup via `resolve_api_call()`
- **UNDEFINED_NAME**: Fuzzy match via `get_by_name()`
- **RUNTIME_ERROR**: Lookup class methods or parameters
- **LOGIC_ERROR**: Query APIs in surrounding scope

Returns deduplicated list of relevant KG entries.

#### `build_kg_context(entries, signatures, token_budget=800)`
Assembles KG entries into markdown within token budget:
- Scores entries by relevance
- Sorts by score (highest first)
- Formats each entry concisely
- Stops when token budget exhausted
- Returns formatted markdown string

#### Helper Functions
- `detect_library(code)`: Identify which DS library is used
- `score_kg_relevance(entry, signatures)`: Relevance scoring
- `format_kg_entry(entry)`: Format single entry as markdown

### 3. Enhanced Prompts (`prompts.py`)

**New Templates**:
- `REPAIR_PROMPT_ERROR_LINE_WITH_KG`: Simple error prompt with KG context
- `REPAIR_PROMPT_TEMPLATE_WITH_KG`: Full template with KG context

**Modified Function**:
```python
def build_repair_prompt(
    apr_input: APRInput,
    patch: GeneratedPatch,
    template: str | None = None,
    auto_select: bool = True,
    kg_engine: Optional[DSKGEngine] = None,  # NEW
    kg_context_budget: int = 800,            # NEW
) -> str:
```

**Behavior**:
1. If `kg_engine` is None: Uses existing behavior (backward compatible)
2. Otherwise:
   - Extracts error signatures from patch
   - Queries KG for relevant entries
   - Builds KG context within token budget
   - Selects KG-enhanced template if context exists
   - Injects KG context into prompt

### 4. Updated PatchGenerator (`generator.py`)

**Modified Constructor**:
```python
class PatchGenerator:
    def __init__(
        self,
        kg_engine: Optional[DSKGEngine] = None,
        kg_context_budget: int = 800
    ):
        self.kg_engine = kg_engine
        self.kg_budget = kg_context_budget
```

**Note**: The generator stores the KG engine but doesn't use it directly. KG integration happens downstream in `build_repair_prompt()`.

## Usage Examples

### Basic Usage (Without KG)

```python
from APR.patch_generation import PatchGenerator, build_repair_prompt

# Generate patch
generator = PatchGenerator()
patch = generator.generate(request)

# Build prompt (no KG)
prompt = build_repair_prompt(apr_input, patch)
```

### With KG Integration

```python
from APR.DS_KG.engine import DSKGEngine
from APR.patch_generation import PatchGenerator, build_repair_prompt

# Load KG
kg_engine = DSKGEngine([
    "APR/DS-KG/kg_numpy.json",
    "APR/DS-KG/kg_pandas.json"
])

# Generate patch
generator = PatchGenerator(kg_engine=kg_engine)
patch = generator.generate(request)

# Build prompt with KG context
prompt = build_repair_prompt(
    apr_input=apr_input,
    patch=patch,
    kg_engine=kg_engine,
    kg_context_budget=800  # Token limit for KG context
)

# Now prompt contains API documentation relevant to the errors!
```

### Complete Repair Pipeline

```python
from APR.DS_KG.engine import DSKGEngine
from APR.patch_generation import PatchGenerator, build_repair_prompt

def repair_with_kg(apr_input, llm_client):
    # Load KG
    kg_engine = DSKGEngine()  # Auto-loads all kg_*.json files
    
    # Generate patch with error markers
    generator = PatchGenerator(kg_engine=kg_engine)
    request = {
        "apr_input": apr_input,
        "patch_strategy": {
            "mode": "multi_hunk",
            "error_focus": "hybrid"
        }
    }
    patch = generator.generate(request)
    
    # Build prompt with KG integration
    prompt = build_repair_prompt(
        apr_input=apr_input,
        patch=patch,
        kg_engine=kg_engine,
        kg_context_budget=800
    )
    
    # Send to LLM for repair
    fixed_code = llm_client.generate(prompt)
    
    return fixed_code
```

## Error Type → KG Query Mapping

| Error Type | KG Query Strategy | Context Provided |
|------------|-------------------|------------------|
| API_ERROR | `resolve_api_call(library, api_name)` | Full entry + alternatives if deprecated |
| UNDEFINED_NAME | `get_by_name(name)` + fuzzy | Import suggestion + usage |
| RUNTIME_ERROR (AttributeError) | `get_class_methods(library, class)` | Available methods |
| RUNTIME_ERROR (TypeError) | `resolve_api_call()` | Parameter requirements |
| LOGIC_ERROR | `get_by_name()` for scope APIs | Usage patterns |
| SYNTAX_ERROR | None | Not API-related |

## Example Prompt Output

When KG integration is active, the prompt includes an API Documentation section:

```markdown
Fix the error in the code below using the provided API documentation.

## API Documentation

### numpy.array
**Required**: ['object']
**Optional**: ['dtype', 'copy', 'order', 'subok', 'ndmin', 'like']
**Returns**: ndarray
array(object, dtype=None, *, copy=True, order='K', subok=False, ndmin=0

## Error
Line 2: NameError: name 'np' is not defined

## Problem
Calculate the mean of a list of numbers using numpy

## Code with Error Marked
```python
def calculate_mean(numbers):
<<<<<<< [ERROR START: UNDEFINED_NAME]
    arr = np.array(numbers)
=======
# Undefined: 'np', did you mean 'numpy'?
import numpy
>>>>>>> [ERROR END: UNDEFINED_NAME]
    return arr.mean()
```

## Instructions
- Refer to API Documentation above for correct usage
- Fix the marked block at line 2
- Remove all marker lines (<<<<<<<, =======, >>>>>>>)
- Return only the corrected code
```

## Token Budget Management

The `kg_context_budget` parameter (default: 800 tokens) limits how much KG context is included:

1. **Relevance Scoring**: Entries are scored by relevance to the specific errors
2. **Priority Ordering**: Highest-scoring entries are included first
3. **Token Tracking**: Simple heuristic (~4 chars = 1 token)
4. **Budget Enforcement**: Stops adding entries when budget reached
5. **Truncation Notice**: Adds notice if not all entries fit

**Tuning the Budget**:
- **Lower (400-600)**: Faster, cheaper, less context
- **Default (800)**: Balanced - typically 2-4 API entries
- **Higher (1000-1500)**: More context, but increases prompt cost

## Backward Compatibility

The integration is **fully backward compatible**:

1. **Optional Parameter**: `kg_engine` defaults to None
2. **Existing Code Works**: All existing code continues to work without modification
3. **No Breaking Changes**: Added parameters are optional with sensible defaults
4. **Graceful Fallback**: If KG query fails, falls back to non-KG prompt

## Testing

Run the demo to see the integration in action:

```bash
cd /path/to/FYP-26
bash APR/examples/run_demo.sh
```

See `APR/examples/README.md` for detailed demo documentation.

## Performance Considerations

1. **KG Loading**: Load once at startup, reuse across multiple repairs
   ```python
   kg_engine = DSKGEngine()  # Load once
   generator = PatchGenerator(kg_engine=kg_engine)  # Reuse
   ```

2. **Query Efficiency**: 
   - Exact lookups are O(1) via path index
   - Fuzzy searches are O(N) but N is small per library
   - Results are deduplicated to avoid redundancy

3. **Memory Usage**:
   - Full KG in memory: ~5-10 MB per library
   - Entries are lightweight TypedDicts
   - Indexed for fast lookup

## Future Enhancements

Potential improvements:

1. **Example Code**: Include short usage examples from KG
2. **Deprecation Warnings**: Highlight deprecated APIs more prominently
3. **Version-Specific Docs**: Use library version from environment
4. **Cross-Library Queries**: Suggest alternative libraries/APIs
5. **Caching**: Cache KG query results for repeated errors
6. **Analytics**: Track which KG entries lead to successful repairs

## Files Modified/Created

**New Files**:
- `APR/DS-KG/__init__.py`
- `APR/DS-KG/engine.py`
- `APR/patch_generation/kg_integration.py`
- `APR/examples/demo_kg_repair.py`
- `APR/examples/run_demo.sh`
- `APR/examples/README.md`

**Modified Files**:
- `APR/patch_generation/prompts.py` - Added KG templates, modified `build_repair_prompt()`
- `APR/patch_generation/generator.py` - Added KG engine parameter
- `APR/patch_generation/__init__.py` - Export KG integration functions

## Support

For issues or questions about the KG integration:
1. Check `APR/examples/demo_kg_repair.py` for working example
2. Review this document for usage patterns
3. Check `APR/DS-KG/ABOUT_SCHEMA.md` for KG structure details
