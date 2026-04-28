#!/bin/bash

# stitch-docs.sh - Concatenate multiple markdown documents
# Usage: ./stitch-docs.sh --files "part1.md part2.md" --output combined.md [options]

set -e

# Default values
FILES=""
OUTPUT=""
REMOVE_HEADERS=false
SECTION_BREAKS=false
VERIFY=false
SKIP_LINES=2

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --files)
      FILES="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --remove-headers)
      REMOVE_HEADERS=true
      shift
      ;;
    --section-breaks)
      SECTION_BREAKS=true
      shift
      ;;
    --verify)
      VERIFY=true
      shift
      ;;
    --skip-lines)
      SKIP_LINES="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 --files \"file1 file2...\" --output output.md [--remove-headers] [--section-breaks] [--verify]"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$FILES" ] || [ -z "$OUTPUT" ]; then
  echo "Error: --files and --output are required"
  echo "Usage: $0 --files \"file1 file2...\" --output output.md"
  exit 1
fi

# Convert FILES string to array
IFS=' ' read -ra FILE_ARRAY <<< "$FILES"

# Check all files exist
for file in "${FILE_ARRAY[@]}"; do
  if [ ! -f "$file" ]; then
    echo "Error: File not found: $file"
    exit 1
  fi
done

echo "Stitching ${#FILE_ARRAY[@]} files into $OUTPUT..."

# Remove output file if exists
rm -f "$OUTPUT"

# Process first file (always include all lines)
cat "${FILE_ARRAY[0]}" > "$OUTPUT"
echo "  ✓ ${FILE_ARRAY[0]} (full content)"

# Process remaining files
for i in "${!FILE_ARRAY[@]}"; do
  if [ $i -eq 0 ]; then
    continue  # Skip first file (already processed)
  fi

  file="${FILE_ARRAY[$i]}"

  # Add section break if requested
  if [ "$SECTION_BREAKS" = true ]; then
    echo -e "\n---\n" >> "$OUTPUT"
  fi

  # Append file content (with or without header removal)
  if [ "$REMOVE_HEADERS" = true ]; then
    tail -n +$((SKIP_LINES + 1)) "$file" >> "$OUTPUT"
    echo "  ✓ $file (skipped first $SKIP_LINES lines)"
  else
    cat "$file" >> "$OUTPUT"
    echo "  ✓ $file (full content)"
  fi
done

# Report results
TOTAL_LINES=$(wc -l < "$OUTPUT")
OUTPUT_SIZE=$(du -h "$OUTPUT" | cut -f1)

echo ""
echo "✅ Stitching complete!"
echo "   Output: $OUTPUT"
echo "   Lines: $TOTAL_LINES"
echo "   Size: $OUTPUT_SIZE"

# Run verification if requested
if [ "$VERIFY" = true ]; then
  echo ""
  echo "Running verification..."
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "$SCRIPT_DIR/verify-stitch.sh" "$OUTPUT" "${FILE_ARRAY[@]}"
fi
