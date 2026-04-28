#!/bin/bash

# pr-faq-stitch.sh - Example: Stitch 4-part PR-FAQ into single document
# This demonstrates the most common use case for doc-stitcher

set -e

# Configuration
REQUIREMENTS_DIR="../../../requirements"
OUTPUT_FILE="$REQUIREMENTS_DIR/productization-pr-faq-STITCHED.md"

# Files to stitch (in order)
FILES=(
  "$REQUIREMENTS_DIR/pr-faq-01-press-release.md"
  "$REQUIREMENTS_DIR/pr-faq-02-external-faq.md"
  "$REQUIREMENTS_DIR/pr-faq-03-internal-faq.md"
  "$REQUIREMENTS_DIR/pr-faq-04-appendices.md"
)

echo "PR-FAQ Stitching Example"
echo "========================"
echo ""
echo "This will stitch 4 PR-FAQ parts into a single document:"
echo "  1. Press Release (Part 1)"
echo "  2. External FAQ (Part 2)"
echo "  3. Internal FAQ (Part 3)"
echo "  4. Appendices (Part 4)"
echo ""
echo "Output: $OUTPUT_FILE"
echo ""

# Check all source files exist
MISSING=0
for file in "${FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "❌ Missing: $file"
    MISSING=1
  else
    LINES=$(wc -l < "$file")
    echo "✓ Found: $(basename "$file") ($LINES lines)"
  fi
done

if [ $MISSING -eq 1 ]; then
  echo ""
  echo "Error: Some source files are missing. Cannot proceed."
  exit 1
fi

echo ""
read -p "Proceed with stitching? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# Stitch files
# Part 1: Full content
cat "${FILES[0]}" > "$OUTPUT_FILE"

# Parts 2-4: Skip first 2 lines (remove "# Part N" header)
for i in {1..3}; do
  echo "" >> "$OUTPUT_FILE"  # Add blank line
  echo "---" >> "$OUTPUT_FILE"  # Add section divider
  echo "" >> "$OUTPUT_FILE"  # Add blank line
  tail -n +3 "${FILES[$i]}" >> "$OUTPUT_FILE"
done

# Report results
TOTAL_LINES=$(wc -l < "$OUTPUT_FILE")
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo ""
echo "✅ Stitching complete!"
echo "   Output: $OUTPUT_FILE"
echo "   Total lines: $TOTAL_LINES"
echo "   File size: $FILE_SIZE"
echo ""
echo "To verify, run:"
echo "   head -50 $OUTPUT_FILE"
echo "   tail -50 $OUTPUT_FILE"
