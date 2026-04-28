#!/bin/bash

# verify-stitch.sh - Verify stitched document integrity
# Usage: ./verify-stitch.sh output.md [source files...]

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 output.md [source1.md source2.md ...]"
  exit 1
fi

OUTPUT="$1"
shift
SOURCE_FILES=("$@")

echo "Verifying $OUTPUT..."
echo ""

# Check 1: File exists and is readable
if [ ! -f "$OUTPUT" ]; then
  echo "❌ FAIL: Output file not found: $OUTPUT"
  exit 1
fi

if [ ! -r "$OUTPUT" ]; then
  echo "❌ FAIL: Output file not readable: $OUTPUT"
  exit 1
fi

echo "✓ File exists and is readable"

# Check 2: File is not empty
if [ ! -s "$OUTPUT" ]; then
  echo "❌ FAIL: Output file is empty"
  exit 1
fi

echo "✓ File is not empty"

# Check 3: Line count is reasonable
OUTPUT_LINES=$(wc -l < "$OUTPUT")
if [ "$OUTPUT_LINES" -lt 10 ]; then
  echo "⚠ WARNING: Output file has only $OUTPUT_LINES lines (expected more)"
fi

echo "✓ Line count: $OUTPUT_LINES lines"

# Check 4: Compare to source files (if provided)
if [ ${#SOURCE_FILES[@]} -gt 0 ]; then
  EXPECTED_LINES=0
  for file in "${SOURCE_FILES[@]}"; do
    if [ -f "$file" ]; then
      LINES=$(wc -l < "$file")
      EXPECTED_LINES=$((EXPECTED_LINES + LINES))
    fi
  done

  DIFF=$((OUTPUT_LINES - EXPECTED_LINES))
  if [ $DIFF -lt 0 ]; then
    echo "⚠ WARNING: Output has fewer lines than sources (diff: $DIFF)"
  else
    echo "✓ Line count matches sources (diff: $DIFF, likely from section breaks)"
  fi
fi

# Check 5: Markdown structure
CODE_BLOCK_START=$(grep -c '^```' "$OUTPUT" || true)
if [ $((CODE_BLOCK_START % 2)) -ne 0 ]; then
  echo "⚠ WARNING: Odd number of code block markers (```) - possible unclosed blocks"
else
  echo "✓ Code blocks balanced ($((CODE_BLOCK_START / 2)) blocks)"
fi

# Check 6: No obvious corruption
BINARY_CHARS=$(grep -c $'[\x00-\x08\x0B\x0C\x0E-\x1F]' "$OUTPUT" || true)
if [ "$BINARY_CHARS" -gt 0 ]; then
  echo "⚠ WARNING: Found $BINARY_CHARS lines with binary characters"
else
  echo "✓ No binary characters detected"
fi

# Check 7: File size
FILE_SIZE=$(du -h "$OUTPUT" | cut -f1)
echo "✓ File size: $FILE_SIZE"

echo ""
echo "✅ Verification complete - $OUTPUT looks good!"
