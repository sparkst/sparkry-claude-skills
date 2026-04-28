#!/usr/bin/env python3
"""
Handout Generator - Create 1-page PDF handouts with key frameworks and takeaways
"""

import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas


# Sparkry Brand Colors
SPARKRY_ORANGE = HexColor('#ff6b35')
SPARKRY_NAVY = HexColor('#171d28')
LIGHT_GRAY = HexColor('#f0f0f0')
DARK_GRAY = HexColor('#646464')


class HandoutContent:
    """Represents extracted content for handout"""
    def __init__(self):
        self.session_title = ""
        self.frameworks = []
        self.statistics = []
        self.action_items = []
        self.key_concepts = []


class HandoutParser:
    """Parse markdown to extract handout-worthy content"""

    def __init__(self, markdown_path: Path):
        self.markdown_path = markdown_path
        self.content = markdown_path.read_text()

    def parse(self) -> HandoutContent:
        """Extract frameworks, stats, and action items"""
        handout = HandoutContent()
        lines = self.content.split('\n')

        in_framework = False
        in_action_items = False
        current_framework = []
        current_framework_name = ""

        for line in lines:
            # Extract session title
            if line.startswith('# ') and not handout.session_title:
                handout.session_title = line[2:].strip()
                continue

            # Extract frameworks
            if '**Framework:**' in line or 'Framework:' in line:
                in_framework = True
                # Extract framework name from the line
                match = re.search(r'\*\*Framework:\*\*\s*(.+)', line)
                if match:
                    current_framework_name = match.group(1).strip()
                continue

            if in_framework:
                if line.strip().startswith('-'):
                    bullet = line.strip()[1:].strip()
                    bullet = re.sub(r'\*\*(.+?)\*\*', r'\1', bullet)
                    current_framework.append(bullet)
                elif line.strip() == '' and current_framework:
                    # End of framework
                    handout.frameworks.append({
                        'name': current_framework_name,
                        'items': current_framework.copy()
                    })
                    current_framework = []
                    current_framework_name = ""
                    in_framework = False

            # Extract statistics (lines with percentages or large numbers)
            if re.search(r'\d+%|\$\d+[BMK]|\d{2,}', line) and line.strip().startswith('-'):
                stat = line.strip()[1:].strip()
                stat = re.sub(r'\*\*(.+?)\*\*', r'\1', stat)
                # Clean up stat to be concise
                if len(stat) < 120:  # Only include concise stats
                    handout.statistics.append(stat)

            # Extract action items
            if '**ACTION ITEMS:**' in line or 'ACTION ITEMS:' in line:
                in_action_items = True
                continue

            if in_action_items:
                if line.strip().startswith('-') or line.strip().startswith('□'):
                    action = line.strip()[1:].strip()
                    if action.startswith('□'):
                        action = action[1:].strip()
                    action = re.sub(r'\*\*(.+?)\*\*', r'\1', action)
                    handout.action_items.append(action)
                elif line.strip() == '':
                    in_action_items = False

            # Extract key concepts (bolded terms in paragraphs)
            if '**' in line and not line.startswith('#') and not line.startswith('-'):
                concepts = re.findall(r'\*\*([^*]+)\*\*', line)
                for concept in concepts:
                    if len(concept) < 50 and concept not in handout.key_concepts:
                        handout.key_concepts.append(concept)

        # Remove duplicates while preserving order
        handout.statistics = list(dict.fromkeys(handout.statistics))[:6]  # Max 6 stats
        handout.key_concepts = list(dict.fromkeys(handout.key_concepts))[:5]  # Max 5 concepts

        return handout


class HandoutGenerator:
    """Generate PDF handout with Sparkry branding"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Create custom paragraph styles with Sparkry branding"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='HandoutTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=SPARKRY_NAVY,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=SPARKRY_ORANGE,
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold',
            borderPadding=4,
            borderColor=SPARKRY_ORANGE,
            borderWidth=0,
            underlineWidth=2,
            underlineColor=SPARKRY_ORANGE
        ))

        # Framework name style
        self.styles.add(ParagraphStyle(
            name='FrameworkName',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=SPARKRY_NAVY,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        # Bullet style
        self.styles.add(ParagraphStyle(
            name='BulletItem',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=SPARKRY_NAVY,
            leftIndent=12,
            spaceAfter=4,
            fontName='Helvetica'
        ))

        # Statistic style
        self.styles.add(ParagraphStyle(
            name='Statistic',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=DARK_GRAY,
            leftIndent=12,
            spaceAfter=4,
            fontName='Helvetica'
        ))

    def _add_header(self, canvas, doc):
        """Add header with orange accent"""
        canvas.saveState()

        # Orange bar at top
        canvas.setFillColor(SPARKRY_ORANGE)
        canvas.rect(0, letter[1] - 0.3*inch, letter[0], 0.3*inch, fill=1, stroke=0)

        canvas.restoreState()

    def _add_footer(self, canvas, doc):
        """Add footer"""
        canvas.saveState()

        # Navy line at bottom
        canvas.setStrokeColor(SPARKRY_NAVY)
        canvas.setLineWidth(2)
        canvas.line(0.5*inch, 0.5*inch, letter[0] - 0.5*inch, 0.5*inch)

        # Page number
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(DARK_GRAY)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawRightString(letter[0] - 0.5*inch, 0.35*inch, text)

        canvas.restoreState()

    def generate(self, content: HandoutContent, output_path: Path):
        """Generate PDF handout"""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            topMargin=0.8*inch,
            bottomMargin=0.8*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )

        story = []

        # Title
        story.append(Paragraph(content.session_title, self.styles['HandoutTitle']))
        story.append(Spacer(1, 0.2*inch))

        # Frameworks Section
        if content.frameworks:
            story.append(Paragraph("KEY FRAMEWORKS", self.styles['SectionHeader']))

            for framework in content.frameworks[:3]:  # Max 3 frameworks
                story.append(Paragraph(framework['name'], self.styles['FrameworkName']))

                for item in framework['items']:
                    bullet_text = f"• {item}"
                    story.append(Paragraph(bullet_text, self.styles['BulletItem']))

                story.append(Spacer(1, 0.1*inch))

        # Statistics Section
        if content.statistics:
            story.append(Paragraph("KEY STATISTICS", self.styles['SectionHeader']))

            for stat in content.statistics:
                bullet_text = f"• {stat}"
                story.append(Paragraph(bullet_text, self.styles['Statistic']))

            story.append(Spacer(1, 0.15*inch))

        # Action Items Section
        if content.action_items:
            story.append(Paragraph("ACTION ITEMS", self.styles['SectionHeader']))

            for action in content.action_items[:5]:  # Max 5 action items
                checkbox_text = f"☐ {action}"
                story.append(Paragraph(checkbox_text, self.styles['BulletItem']))

            story.append(Spacer(1, 0.15*inch))

        # Key Concepts Section
        if content.key_concepts:
            story.append(Paragraph("KEY CONCEPTS", self.styles['SectionHeader']))

            concepts_text = " • ".join(content.key_concepts)
            story.append(Paragraph(concepts_text, self.styles['BulletItem']))

        # Build PDF
        doc.build(
            story,
            onFirstPage=self._add_header,
            onLaterPages=self._add_header
        )

        print(f"✅ Generated handout: {output_path}")
        print(f"   - {len(content.frameworks)} frameworks")
        print(f"   - {len(content.statistics)} statistics")
        print(f"   - {len(content.action_items)} action items")


def main():
    parser = argparse.ArgumentParser(
        description="Generate 1-page PDF handout from markdown training content"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Input markdown file path"
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output PDF file path"
    )

    args = parser.parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return 1

    # Create output directory if needed
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Parse markdown
    print(f"📖 Parsing markdown for handout: {args.input}")
    parser = HandoutParser(args.input)
    content = parser.parse()

    print(f"   - Session: {content.session_title}")

    # Generate handout
    print("🎨 Generating handout with Sparkry branding...")
    generator = HandoutGenerator()
    generator.generate(content, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
