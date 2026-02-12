"""
DS-KG Validation Script
-----------------------
Validates KG improvements by comparing:
- Parameter coverage (functions with params vs without)
- Total function/class counts
- Specific critical functions
"""

import json
import os
from datetime import datetime

# Critical functions to verify
CRITICAL_FUNCTIONS = {
    "numpy": ["array", "zeros", "ones", "mean", "sum", "arange", "linspace"],
    "scipy": ["stats.norm", "linalg.inv", "optimize.minimize"],
    "sklearn": [
        "linear_model.LinearRegression",
        "tree.DecisionTreeClassifier",
        "preprocessing.StandardScaler"
    ],
}

def load_kg(filename):
    """Load a KG JSON file."""
    if not os.path.exists(filename):
        return None
    with open(filename) as f:
        return json.load(f)

def analyze_kg(kg):
    """Analyze a KG and return metrics."""
    if not kg:
        return None
    
    functions = kg.get("functions", {})
    classes = kg.get("classes", {})
    modules = kg.get("modules", {})
    
    # Count functions with/without parameters
    funcs_with_params = 0
    funcs_without_params = 0
    
    for func_name, func in functions.items():
        params = func.get("parameters", {})
        required = params.get("required", [])
        optional = params.get("optional", [])
        
        if required or optional:
            funcs_with_params += 1
        else:
            funcs_without_params += 1
    
    total_funcs = len(functions)
    param_coverage = (funcs_with_params / total_funcs * 100) if total_funcs > 0 else 0
    
    return {
        "library": kg.get("library"),
        "modules": len(modules),
        "classes": len(classes),
        "functions": total_funcs,
        "functions_with_params": funcs_with_params,
        "functions_without_params": funcs_without_params,
        "param_coverage_pct": round(param_coverage, 1),
    }

def check_critical_functions(kg, library_name):
    """Check if critical functions exist and have parameters."""
    if library_name not in CRITICAL_FUNCTIONS:
        return []
    
    functions = kg.get("functions", {})
    results = []
    
    for func_path in CRITICAL_FUNCTIONS[library_name]:
        exists = func_path in functions
        has_params = False
        
        if exists:
            func = functions[func_path]
            params = func.get("parameters", {})
            required = params.get("required", [])
            optional = params.get("optional", [])
            has_params = bool(required or optional)
        
        results.append({
            "function": func_path,
            "exists": exists,
            "has_params": has_params,
            "status": "✓" if (exists and has_params) else ("⚠" if exists else "✗")
        })
    
    return results

def compare_before_after(backup_dir):
    """Compare backup KGs with current KGs."""
    libraries = [
        "numpy", "pandas", "matplotlib_pyplot", 
        "scipy", "sklearn", "seaborn", "statsmodels_api"
    ]
    
    print("=" * 80)
    print("DS-KG VALIDATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    comparison = {}
    
    for lib in libraries:
        filename = f"kg_{lib}.json"
        backup_path = os.path.join(backup_dir, filename)
        current_path = filename
        
        before = load_kg(backup_path)
        after = load_kg(current_path)
        
        before_metrics = analyze_kg(before) if before else None
        after_metrics = analyze_kg(after) if after else None
        
        comparison[lib] = {
            "before": before_metrics,
            "after": after_metrics
        }
    
    # Print comparison table
    print("1. COVERAGE COMPARISON")
    print("-" * 80)
    print(f"{'Library':<20} {'Functions':<15} {'Param Coverage':<20} {'Status'}")
    print(f"{'':20} {'Before → After':<15} {'Before → After':<20}")
    print("-" * 80)
    
    for lib, data in comparison.items():
        before = data["before"]
        after = data["after"]
        
        if not before or not after:
            print(f"{lib:<20} {'N/A':<15} {'N/A':<20} {'ERROR'}")
            continue
        
        func_change = f"{before['functions']} → {after['functions']}"
        coverage_change = f"{before['param_coverage_pct']}% → {after['param_coverage_pct']}%"
        
        # Determine status
        if after['param_coverage_pct'] > before['param_coverage_pct']:
            status = "✓ IMPROVED"
        elif after['param_coverage_pct'] == before['param_coverage_pct']:
            status = "= UNCHANGED"
        else:
            status = "✗ REGRESSED"
        
        print(f"{lib:<20} {func_change:<15} {coverage_change:<20} {status}")
    
    # Print detailed improvements
    print("\n2. DETAILED IMPROVEMENTS")
    print("-" * 80)
    
    for lib, data in comparison.items():
        before = data["before"]
        after = data["after"]
        
        if not before or not after:
            continue
        
        print(f"\n{lib.upper()}:")
        print(f"  Modules:    {before['modules']} → {after['modules']}")
        print(f"  Classes:    {before['classes']} → {after['classes']}")
        print(f"  Functions:  {before['functions']} → {after['functions']}")
        print(f"  With Params: {before['functions_with_params']} → {after['functions_with_params']}")
        print(f"  Coverage:   {before['param_coverage_pct']}% → {after['param_coverage_pct']}%")
    
    # Check critical functions
    print("\n3. CRITICAL FUNCTIONS VERIFICATION")
    print("-" * 80)
    
    for lib in ["numpy", "scipy", "sklearn"]:
        if lib not in comparison:
            continue
        
        after = comparison[lib]["after"]
        if not after:
            continue
        
        filename = f"kg_{lib}.json"
        kg = load_kg(filename)
        if not kg:
            continue
        
        print(f"\n{lib.upper()}:")
        critical = check_critical_functions(kg, lib)
        for item in critical:
            print(f"  {item['status']} {item['function']:<40} "
                  f"{'EXISTS' if item['exists'] else 'MISSING':<10} "
                  f"{'PARAMS: YES' if item['has_params'] else 'PARAMS: NO'}")
    
    # Summary
    print("\n4. VALIDATION SUMMARY")
    print("-" * 80)
    
    improvements = 0
    unchanged = 0
    regressions = 0
    
    for lib, data in comparison.items():
        before = data["before"]
        after = data["after"]
        
        if not before or not after:
            continue
        
        if after['param_coverage_pct'] > before['param_coverage_pct']:
            improvements += 1
        elif after['param_coverage_pct'] == before['param_coverage_pct']:
            unchanged += 1
        else:
            regressions += 1
    
    print(f"Libraries improved: {improvements}")
    print(f"Libraries unchanged: {unchanged}")
    print(f"Libraries regressed: {regressions}")
    
    # Save to JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "comparison": comparison,
        "summary": {
            "improved": improvements,
            "unchanged": unchanged,
            "regressed": regressions
        }
    }
    
    with open("validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: validation_report.json")
    print("=" * 80)
    
    return regressions == 0

if __name__ == "__main__":
    import sys
    
    # Find most recent backup directory
    backup_dirs = [d for d in os.listdir('.') if d.startswith('backup_')]
    if not backup_dirs:
        print("Error: No backup directory found!")
        sys.exit(1)
    
    backup_dir = sorted(backup_dirs)[-1]
    print(f"Comparing against backup: {backup_dir}\n")
    
    success = compare_before_after(backup_dir)
    sys.exit(0 if success else 1)
