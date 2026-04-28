#!/bin/bash
# Install dependencies for PowerPoint generation skill

set -e

echo "📦 Installing Python dependencies for PowerPoint generation..."

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 not found. Please install Python 3 first."
    exit 1
fi

# Install required packages
echo "Installing python-pptx..."
pip3 install python-pptx

echo "Installing reportlab (for PDF handouts)..."
pip3 install reportlab

echo "Installing Pillow (for image handling)..."
pip3 install Pillow

echo ""
echo "✅ All dependencies installed successfully!"
echo ""
echo "You can now use:"
echo "  - generate-presentation.py to create PowerPoint files"
echo "  - create-handout.py to create PDF handouts"
