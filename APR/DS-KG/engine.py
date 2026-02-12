"""
DS-KG Query Engine
------------------
Load and query Knowledge Graph JSON files for API documentation.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, TypedDict


class DSKGEntry(TypedDict, total=False):
    """Single KG entry (function/class/method)."""
    node_type: str  # "function", "class", "method", "module"
    name: str  # API name (e.g., "array", "DataFrame")
    path: str  # Full path (e.g., "numpy.array")
    library: str  # Library name (e.g., "numpy", "pandas")
    module: str  # Module path
    parameters: Dict[str, List[str]]  # {"required": [...], "optional": [...]}
    returns: str  # Return type description
    description: str  # Short description
    deprecated: bool  # Whether API is deprecated
    alternatives: List[str]  # Alternative APIs (for deprecated)
    methods: List[str]  # Methods (for classes)
    attributes: List[str]  # Attributes (for classes)
    belongs_to: Optional[str]  # Parent class (for methods)
    raw_data: Dict[str, Any]  # Full raw entry


class DSKGEngine:
    """Query engine for DS-KG knowledge graphs."""
    
    def __init__(self, kg_paths: Optional[List[str]] = None):
        """
        Initialize KG engine with JSON files.
        
        Args:
            kg_paths: List of paths to KG JSON files. If None, loads all
                     kg_*.json files from APR/DS-KG/ directory.
        """
        self.entries: Dict[str, DSKGEntry] = {}  # path -> entry
        self.library_entries: Dict[str, List[DSKGEntry]] = {}  # library -> entries
        self.name_index: Dict[str, List[DSKGEntry]] = {}  # name -> entries
        
        if kg_paths is None:
            # Auto-discover KG files
            kg_dir = os.path.dirname(os.path.abspath(__file__))
            kg_paths = [
                os.path.join(kg_dir, f)
                for f in os.listdir(kg_dir)
                if f.startswith("kg_") and f.endswith(".json")
            ]
        
        for path in kg_paths:
            if os.path.exists(path):
                self._load_kg_file(path)
    
    def _load_kg_file(self, path: str) -> None:
        """Load a single KG JSON file."""
        with open(path, 'r') as f:
            kg_data = json.load(f)
        
        library = kg_data.get("library", "unknown")
        
        # Index functions
        for name, func_data in kg_data.get("functions", {}).items():
            entry = self._create_entry(library, name, func_data)
            self._index_entry(entry)
        
        # Index classes
        for name, class_data in kg_data.get("classes", {}).items():
            entry = self._create_entry(library, name, class_data)
            self._index_entry(entry)
    
    def _create_entry(
        self,
        library: str,
        name: str,
        data: Dict[str, Any]
    ) -> DSKGEntry:
        """Create a DSKGEntry from raw KG data."""
        node_type = data.get("node_type", "unknown")
        module = data.get("module", library)
        
        # Build full path
        if node_type == "method" and "belongs_to" in data:
            # Method: library.ClassName.method_name
            belongs_to = data["belongs_to"]
            path = f"{library}.{belongs_to}.{name}"
        else:
            # Function or class: library.name or library.submodule.name
            if "." in name:
                path = f"{library}.{name}"
            else:
                path = f"{library}.{name}"
        
        # Extract parameters
        params = data.get("parameters", {})
        if isinstance(params, dict):
            required = params.get("required", [])
            optional = params.get("optional", [])
        else:
            required = []
            optional = []
        
        # Check for deprecation (heuristic - check description)
        description = data.get("description", "")
        deprecated = "deprecated" in description.lower()
        alternatives = []
        if deprecated:
            # Try to extract alternatives from description
            # This is a simple heuristic
            if "use" in description.lower():
                alternatives = self._extract_alternatives(description)
        
        entry: DSKGEntry = {
            "node_type": node_type,
            "name": name,
            "path": path,
            "library": library,
            "module": module,
            "parameters": {"required": required, "optional": optional},
            "returns": data.get("returns", "unknown"),
            "description": description,
            "deprecated": deprecated,
            "alternatives": alternatives,
            "methods": data.get("methods", []),
            "attributes": data.get("attributes", []),
            "belongs_to": data.get("belongs_to"),
            "raw_data": data,
        }
        
        return entry
    
    def _extract_alternatives(self, description: str) -> List[str]:
        """Extract alternative API names from deprecation message."""
        # Simple pattern matching for common deprecation messages
        alternatives = []
        desc_lower = description.lower()
        
        # Look for patterns like "use X instead", "replaced by X", etc.
        import re
        patterns = [
            r"use\s+([a-zA-Z_\.]+)",
            r"replaced\s+by\s+([a-zA-Z_\.]+)",
            r"instead\s+of.*use\s+([a-zA-Z_\.]+)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, desc_lower)
            alternatives.extend(matches)
        
        return list(set(alternatives))[:3]  # Max 3 alternatives
    
    def _index_entry(self, entry: DSKGEntry) -> None:
        """Add entry to all indices."""
        path = entry["path"]
        library = entry["library"]
        name = entry["name"]
        
        # Path index
        self.entries[path] = entry
        
        # Library index
        if library not in self.library_entries:
            self.library_entries[library] = []
        self.library_entries[library].append(entry)
        
        # Name index (for fuzzy lookup)
        name_lower = name.lower()
        if name_lower not in self.name_index:
            self.name_index[name_lower] = []
        self.name_index[name_lower].append(entry)
    
    def resolve_api_call(
        self,
        library: str,
        api_name: str
    ) -> Optional[DSKGEntry]:
        """
        Exact lookup for library.api_name.
        
        Args:
            library: Library name (e.g., "numpy", "pandas")
            api_name: API name (e.g., "array", "DataFrame")
        
        Returns:
            DSKGEntry if found, None otherwise
        """
        # Try exact path
        path = f"{library}.{api_name}"
        if path in self.entries:
            return self.entries[path]
        
        # Try searching in library entries
        if library in self.library_entries:
            for entry in self.library_entries[library]:
                if entry["name"] == api_name or entry["path"].endswith(f".{api_name}"):
                    return entry
        
        return None
    
    def get_by_name(self, name: str, library: Optional[str] = None) -> List[DSKGEntry]:
        """
        Fuzzy lookup by name across all libraries.
        
        Args:
            name: API name to search for
            library: Optional library filter
        
        Returns:
            List of matching entries, sorted by relevance
        """
        name_lower = name.lower()
        matches = []
        
        # Exact name match
        if name_lower in self.name_index:
            matches.extend(self.name_index[name_lower])
        
        # Partial name match (contains)
        for indexed_name, entries in self.name_index.items():
            if name_lower in indexed_name and indexed_name != name_lower:
                matches.extend(entries)
        
        # Filter by library if specified
        if library:
            matches = [e for e in matches if e["library"] == library]
        
        # Remove duplicates
        seen_paths = set()
        unique_matches = []
        for entry in matches:
            if entry["path"] not in seen_paths:
                seen_paths.add(entry["path"])
                unique_matches.append(entry)
        
        return unique_matches
    
    def get_class_methods(
        self,
        library: str,
        class_name: str
    ) -> Optional[DSKGEntry]:
        """
        Get class entry with methods for AttributeError cases.
        
        Args:
            library: Library name
            class_name: Class name
        
        Returns:
            Class entry with methods list, or None
        """
        entry = self.resolve_api_call(library, class_name)
        if entry and entry.get("node_type") == "class":
            return entry
        return None
    
    def list_libraries(self) -> List[str]:
        """Get list of all loaded libraries."""
        return list(self.library_entries.keys())
    
    def get_library_stats(self) -> Dict[str, int]:
        """Get statistics about loaded KG data."""
        return {
            lib: len(entries)
            for lib, entries in self.library_entries.items()
        }
