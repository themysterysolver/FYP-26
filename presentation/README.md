# APR Pipeline Demonstration Notebook

## Overview

This Jupyter Notebook provides a comprehensive demonstration of the Automatic Program Repair (APR) system for your professor. It covers the complete pipeline from hallucination detection through successful code repair.

## Notebook Contents

### Complete Sections (10 Total)

1. **Introduction and Architecture** - Project motivation, pipeline diagram, key statistics
2. **Static Analysis** - AST, CFG, SSA, LIB_API demonstrations with examples
3. **Dynamic Analysis** - Test generation (BVA, ECP), execution, error detection
4. **Data Science Knowledge Graph** - Coverage statistics, query examples, API documentation
5. **Patch Generation** - Git conflict-style markers for all error types
6. **LLM Repair Prompting** - Simple vs rich prompts, KG enhancement, decision trees
7. **End-to-End Examples** - 5 complete repair workflows (syntax, API, logic, runtime, undefined)
8. **Efficiency Comparison** - Structured APR vs naive LLM prompting with quantitative metrics
9. **Results and Statistics** - Aggregate analysis, visualizations (Sankey, charts, heatmaps)
10. **Summary** - Key achievements, innovations, future work

## Features

- **78 Total Cells** with code examples and visualizations
- **Real Data** from your 1,491 processed examples
- **Interactive Visualizations** using Plotly and Matplotlib
- **Syntax Highlighting** for code examples
- **Key Takeaways** after each major section
- **Comprehensive Metrics** demonstrating efficiency gains

## Requirements

### Python Packages

```bash
# Core packages
pip install jupyter notebook

# Data analysis
pip install pandas numpy

# Visualization
pip install plotly matplotlib seaborn

# Code highlighting
pip install pygments

# Optional (for KG demos)
pip install networkx
```

### Data Files

The notebook expects these files to be present (relative to project root):
- `APR/input/apr_input.jsonl` (1,491 entries)
- `Hallucination detection/static/AST/ast_summary.csv`
- `Hallucination detection/static/CFG/cfg_summary.csv`
- `Hallucination detection/static/LIB_API/libapi_summary.csv`
- `Hallucination detection/dynamic/dynamic_summary.csv`
- `APR/DS-KG/validation_report.json`
- `APR/DS-KG/kg_numpy.json` (optional, for live KG demos)

## Running the Notebook

### Option 1: Jupyter Notebook (Recommended)

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
jupyter notebook apr_pipeline_demo.ipynb
```

This will open the notebook in your browser where you can:
- Run cells interactively
- View visualizations
- Modify examples
- Export to HTML/PDF

### Option 2: Jupyter Lab

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
jupyter lab apr_pipeline_demo.ipynb
```

### Option 3: VS Code (with Jupyter extension)

Simply open `apr_pipeline_demo.ipynb` in VS Code with the Jupyter extension installed.

## Exporting the Notebook

### Export to HTML (for presentation)

```bash
jupyter nbconvert --to html apr_pipeline_demo.ipynb
```

This creates `apr_pipeline_demo.html` that can be viewed in any browser.

### Export to PDF (requires additional setup)

```bash
# Install nbconvert with PDF support
pip install nbconvert[webpdf]

# Export
jupyter nbconvert --to pdf apr_pipeline_demo.ipynb
```

### Export to Slides (for live presentation)

```bash
jupyter nbconvert --to slides apr_pipeline_demo.ipynb --post serve
```

This creates a reveal.js slideshow.

## Key Highlights for Your Professor

### 1. Comprehensive Coverage
- All 3 modules demonstrated: Detection, KG, Repair
- Real examples from your 1,491 processed cases
- Both static (AST, CFG, SSA, LIB_API) and dynamic analysis

### 2. Efficiency Gains (Section 8)
- **25% fewer tokens** per repair
- **46% higher success rate** vs naive prompting
- **29% fewer LLM iterations** needed
- **$$ cost savings** demonstrated at scale

### 3. Real Examples (Section 7)
- 5 complete repair workflows
- Each shows: broken code → detection → patch → prompt → repair → validation
- Covers all major error types

### 4. Visualizations
- Pipeline flowcharts (Mermaid)
- Statistical charts (Plotly)
- Sankey diagrams showing data flow
- Radar charts comparing approaches
- Before/after code comparisons

### 5. Knowledge Graph Impact
- 7 libraries, ~2,500 API entries
- Parameter coverage improved 42.6% for numpy
- Prevents API hallucinations

## Troubleshooting

### "Module not found" errors

Install missing packages:
```bash
pip install <package_name>
```

### Data files not found

Check that you're running from the correct directory and all data files exist.

### Visualizations not rendering

Ensure you have the latest version of plotly:
```bash
pip install --upgrade plotly
```

### Mermaid diagrams not showing

Mermaid rendering in Jupyter requires either:
1. JupyterLab with mermaid extension
2. Or view the exported HTML version (Mermaid works in browsers)

## Structure

```
presentation/
├── apr_pipeline_demo.ipynb      # Main notebook (78 cells)
├── README.md                     # This file
├── build_notebook.py            # Builder script (section 2-3)
├── build_notebook_part2.py      # Builder script (section 4-5)
├── build_notebook_final.py      # Builder script (section 6-7)
└── build_notebook_complete.py   # Builder script (section 8-10)
```

## Tips for Presentation

1. **Run All Cells** before presenting to ensure no errors
2. **Hide Code Cells** if professor wants to focus on results:
   - In Jupyter: View → Cell Toolbar → None
3. **Use TOC** navigation links to jump between sections
4. **Pause at Key Takeaways** - highlighted boxes summarize each section
5. **Interactive Q&A** - can modify examples on the fly

## Statistics Summary

- **Total Cells**: 78
- **Code Cells**: ~55
- **Markdown Cells**: ~23
- **Visualizations**: ~15
- **Complete Examples**: 5 end-to-end repairs
- **Error Types Covered**: 10+
- **Datasets**: 3 (MBPP, HumanEval, DS-1000)
- **Total Examples**: 1,491

## Contact

If you encounter any issues or have questions about the notebook:
- Check the inline comments in each cell
- Review the Key Takeaway boxes for summaries
- All code is documented and runnable

---

**Created**: February 2026  
**For**: Professor Presentation  
**Topic**: Automatic Program Repair with Hallucination Detection and Knowledge Graph Integration
