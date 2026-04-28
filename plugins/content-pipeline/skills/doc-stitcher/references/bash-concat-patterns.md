# Bash Concatenation Patterns

Best practices for concatenating files using bash commands.

---

## Basic Concatenation

### Simple Merge
```bash
cat file1.md file2.md file3.md > combined.md
```

### With Glob Pattern (Order Matters!)
```bash
# ✅ GOOD: Explicit ordering
cat part-01-*.md part-02-*.md part-03-*.md > combined.md

# ❌ BAD: Glob may sort unexpectedly
cat part-*.md > combined.md  # May not respect 01, 02, 03 order
```

### Append Mode
```bash
cat file1.md > combined.md   # Create/overwrite
cat file2.md >> combined.md  # Append
cat file3.md >> combined.md  # Append
```

---

## Header Removal

### Skip First N Lines
```bash
# Skip first 2 lines of file2.md
tail -n +3 file2.md >> combined.md
```

### Skip Header from All But First File
```bash
cat part1.md > combined.md
tail -n +3 part2.md >> combined.md
tail -n +3 part3.md >> combined.md
```

### Using Loop
```bash
for file in part*.md; do
  if [ "$file" == "part1.md" ]; then
    cat "$file" > combined.md
  else
    tail -n +3 "$file" >> combined.md
  fi
done
```

---

## Section Breaks

### Add Dividers
```bash
cat part1.md > combined.md
echo -e "\n---\n" >> combined.md
cat part2.md >> combined.md
echo -e "\n---\n" >> combined.md
cat part3.md >> combined.md
```

### Using Heredoc for Complex Breaks
```bash
cat part1.md > combined.md
cat >> combined.md << 'EOF'

---

# Part 2: External FAQ

EOF
cat part2.md >> combined.md
```

---

## Handling Special Cases

### File Paths with Spaces
```bash
# ✅ GOOD: Use quotes
cat "part 1.md" "part 2.md" > "combined file.md"

# ❌ BAD: No quotes
cat part 1.md part 2.md > combined file.md  # Will fail
```

### Check File Existence
```bash
for file in part1.md part2.md part3.md; do
  if [ ! -f "$file" ]; then
    echo "Error: $file not found"
    exit 1
  fi
done

# Now safe to concatenate
cat part1.md part2.md part3.md > combined.md
```

### Preserve Newlines
```bash
# Ensure newline at end of each file
for file in part*.md; do
  cat "$file" >> combined.md
  echo "" >> combined.md  # Add newline
done
```

---

## Performance Considerations

### Large Files
```bash
# For very large files, use direct file descriptors
exec 3> combined.md  # Open file descriptor
cat file1.md >&3
cat file2.md >&3
cat file3.md >&3
exec 3>&-  # Close file descriptor
```

### Parallel Processing (Advanced)
```bash
# Process parts in parallel, then concatenate
cat part1.md > combined.md &
cat part2.md > temp2.md &
cat part3.md > temp3.md &
wait
cat temp2.md temp3.md >> combined.md
rm temp2.md temp3.md
```

---

## Common Pitfalls

### 1. Wrong Order
```bash
# ❌ BAD: Glob may not respect numerical order
cat part-*.md > combined.md
# Might produce: part-1.md, part-10.md, part-2.md...

# ✅ GOOD: Explicit ordering
cat part-01.md part-02.md part-03.md part-10.md > combined.md
```

### 2. Overwriting Source Files
```bash
# ❌ DANGEROUS: Overwrites part1.md
cat part1.md part2.md > part1.md

# ✅ SAFE: Use different output name
cat part1.md part2.md > combined.md
```

### 3. Encoding Issues
```bash
# Check encoding before concatenating
file part1.md part2.md part3.md
# Expected: "UTF-8 Unicode text"

# Convert if needed
iconv -f ISO-8859-1 -t UTF-8 part2.md > part2-utf8.md
```

### 4. Line Ending Differences
```bash
# Check line endings
file part1.md
# "with CRLF line terminators" = Windows
# "with LF line terminators" = Unix

# Convert Windows to Unix
dos2unix part*.md

# Or use sed
sed -i 's/\r$//' part*.md
```

---

## Verification

### Check Line Count
```bash
# Count lines in source files
wc -l part*.md

# Count lines in output
wc -l combined.md

# Compare
# Output should equal sum of sources (minus removed headers)
```

### Check for Corruption
```bash
# Look for binary characters
grep -c $'[\x00-\x08\x0B\x0C\x0E-\x1F]' combined.md

# Should output: 0
```

### Visual Inspection
```bash
# Check beginning and end
head -50 combined.md
tail -50 combined.md

# Check for duplicate headers
grep "^# " combined.md
```

---

## References

- Bash manual: `man bash`
- cat manual: `man cat`
- tail manual: `man tail`
- File command: `man file`
