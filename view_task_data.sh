#!/bin/bash
# Simple script to view all module data for a specific task
# Usage: ./view_task_data.sh DS0001 DS1000

set -e

TASK_ID="$1"
DATASET="$2"

if [ -z "$TASK_ID" ] || [ -z "$DATASET" ]; then
    echo "Usage: ./view_task_data.sh <TASK_ID> <DATASET>"
    echo "Example: ./view_task_data.sh DS0001 DS1000"
    echo "Example: ./view_task_data.sh HumanEval/0 HumanEval"
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "================================================================================"
echo "  Viewing Module Data for: $DATASET / $TASK_ID"
echo "================================================================================"
echo ""

# 1. Generated Code
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. GENERATED CODE (Input to all modules)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
case "$DATASET" in
    DS1000)
        GEN_FILE="$PROJECT_ROOT/Code generation/Qwen/ds1k_gen.csv"
        CODE_COL="full_code"
        ;;
    HumanEval)
        GEN_FILE="$PROJECT_ROOT/Code generation/Qwen/humaneval_gen.csv"
        CODE_COL="GENERATED_CODE"
        ;;
    MBPP)
        GEN_FILE="$PROJECT_ROOT/Code generation/Qwen/mbpp_gen.csv"
        CODE_COL="GENERATED_CODE"
        ;;
    *)
        echo "Unknown dataset: $DATASET"
        exit 1
        ;;
esac

if [ -f "$GEN_FILE" ]; then
    echo "Source: $GEN_FILE"
    echo "Looking for task_id: $TASK_ID"
    echo ""
    # Note: This is a simple grep, may not work perfectly with CSV escaping
    grep "^$TASK_ID," "$GEN_FILE" 2>/dev/null | head -1 || echo "❌ Task not found in generation file"
else
    echo "❌ Generation file not found: $GEN_FILE"
fi

echo ""
echo ""

# 2. AST Result
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. AST ANALYSIS RESULT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

AST_FILE="$PROJECT_ROOT/Hallucination detection/static/AST/ast_${DATASET,,}.jsonl"
if [ -f "$AST_FILE" ]; then
    echo "Source: $AST_FILE"
    echo ""
    grep "\"task_id\": \"$TASK_ID\"" "$AST_FILE" 2>/dev/null | python3 -m json.tool || echo "❌ Task not found in AST results"
else
    echo "❌ AST result file not found: $AST_FILE"
fi

echo ""
echo ""

# 3. CFG Result
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. CFG ANALYSIS RESULT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CFG_FILE="$PROJECT_ROOT/Hallucination detection/static/CFG/cfg_${DATASET,,}.jsonl"
if [ -f "$CFG_FILE" ]; then
    echo "Source: $CFG_FILE"
    echo ""
    grep "\"task_id\": \"$TASK_ID\"" "$CFG_FILE" 2>/dev/null | python3 -m json.tool || echo "❌ Task not found in CFG results"
else
    echo "❌ CFG result file not found: $CFG_FILE"
fi

echo ""
echo ""

# 4. LIB_API Result
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. LIB_API ANALYSIS RESULT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

LIBAPI_FILE="$PROJECT_ROOT/Hallucination detection/static/LIB_API/libapi_${DATASET,,}.jsonl"
if [ -f "$LIBAPI_FILE" ]; then
    echo "Source: $LIBAPI_FILE"
    echo ""
    grep "\"task_id\": \"$TASK_ID\"" "$LIBAPI_FILE" 2>/dev/null | python3 -m json.tool || echo "❌ Task not found in LIB_API results"
else
    echo "❌ LIB_API result file not found: $LIBAPI_FILE"
fi

echo ""
echo ""

# 5. Dynamic Result
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. DYNAMIC EXECUTION RESULT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DYNAMIC_FILE="$PROJECT_ROOT/Hallucination detection/dynamic/dynamic_${DATASET,,}.jsonl"
if [ -f "$DYNAMIC_FILE" ]; then
    echo "Source: $DYNAMIC_FILE"
    echo ""
    grep "\"task_id\": \"$TASK_ID\"" "$DYNAMIC_FILE" 2>/dev/null | python3 -m json.tool || echo "❌ Task not found in dynamic results"
else
    echo "❌ Dynamic result file not found: $DYNAMIC_FILE"
fi

echo ""
echo ""

# 6. APR Input
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. UNIFIED APR INPUT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

APR_FILE="$PROJECT_ROOT/APR/input/apr_input.jsonl"
if [ -f "$APR_FILE" ]; then
    echo "Source: $APR_FILE"
    echo ""
    # APR uses different format: "DS-1000_DS0001" instead of just "DS0001"
    case "$DATASET" in
        DS1000)
            APR_TASK_ID="DS-1000_$TASK_ID"
            ;;
        *)
            APR_TASK_ID="${DATASET}_$TASK_ID"
            ;;
    esac
    grep "\"task_id\": \"$APR_TASK_ID\"" "$APR_FILE" 2>/dev/null | python3 -m json.tool || echo "❌ Task not found in APR input (looking for: $APR_TASK_ID)"
else
    echo "❌ APR input file not found: $APR_FILE"
fi

echo ""
echo ""
echo "================================================================================"
echo "  Data Flow Summary"
echo "================================================================================"
echo ""
echo "File Locations:"
echo "  • Input:   $GEN_FILE"
echo "  • AST:     $AST_FILE"
echo "  • CFG:     $CFG_FILE"
echo "  • LIB_API: $LIBAPI_FILE"
echo "  • Dynamic: $DYNAMIC_FILE"
echo "  • APR:     $APR_FILE"
echo ""
echo "================================================================================"
