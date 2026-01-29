#!/usr/bin/env python3
"""
Quality Scorer

Scores content on 5 metrics (0-100 scale):
1. Groundedness: Citation coverage and source quality
2. Relevance: Content serves reader's goal
3. Readability: Hemingway score, clarity, scannability
4. Voice: Matches persona patterns
5. Originality: Unique insights, avoids clichés

Usage:
    python quality-scorer.py <content_file> [--persona strategic]

Output (JSON):
    {
      "overall": 87,
      "scores": {
        "groundedness": 90,
        "relevance": 85,
        "readability": 88,
        "voice": 84,
        "originality": 88
      },
      "issues": [
        {
          "metric": "voice",
          "priority": "P1",
          "location": "paragraph 3",
          "issue": "Generic AI phrase: 'it's important to note'",
          "fix": "Remove hedge or replace with direct statement"
        }
      ],
      "recommendation": "publish|revise|needs_human_review"
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
import argparse


def extract_claims(content: str) -> List[str]:
    """Extract factual claims from content."""
    # Simple heuristic: Sentences with specific data/statistics
    sentences = re.split(r'[.!?]+', content)

    claims = []
    claim_indicators = [
        r'\d+%',  # Percentages
        r'\d+[KMB]',  # Numbers with K/M/B suffix
        r'\d{4}',  # Years
        r'study shows',
        r'research indicates',
        r'data reveals',
        r'according to'
    ]

    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in claim_indicators):
            claims.append(sentence.strip())

    return claims


def extract_citations(content: str) -> List[Dict[str, Any]]:
    """Extract citations from content."""
    # Markdown link pattern
    citations = []

    # Pattern: [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

    for text, url in markdown_links:
        # Classify tier based on domain
        tier = classify_source_tier(url)
        citations.append({
            'text': text,
            'url': url,
            'tier': tier
        })

    return citations


def classify_source_tier(url: str) -> int:
    """Classify source tier (1=highest, 3=lowest)."""
    url_lower = url.lower()

    # Tier 1: Academic, government, primary research
    tier1_domains = ['.edu', '.gov', 'arxiv.org', 'nih.gov', 'ieee.org']
    if any(domain in url_lower for domain in tier1_domains):
        return 1

    # Tier 2: Industry, professional
    tier2_domains = ['hbr.org', 'economist.com', 'openai.com', 'anthropic.com']
    if any(domain in url_lower for domain in tier2_domains):
        return 2

    # Tier 3: Everything else
    return 3


def score_groundedness(content: str) -> tuple[int, List[Dict[str, Any]]]:
    """Score groundedness (0-100) based on citation coverage."""
    claims = extract_claims(content)
    citations = extract_citations(content)

    issues = []

    if not claims:
        return 100, []  # No claims = nothing to cite

    # Calculate citation coverage
    cited_ratio = min(1.0, len(citations) / len(claims))

    # Tier scoring
    if citations:
        tier1_ratio = len([c for c in citations if c['tier'] == 1]) / len(citations)
        tier2_ratio = len([c for c in citations if c['tier'] == 2]) / len(citations)
        tier_bonus = (tier1_ratio * 10) + (tier2_ratio * 5)
    else:
        tier_bonus = 0
        issues.append({
            'metric': 'groundedness',
            'priority': 'P0',
            'location': 'general',
            'issue': 'No citations found',
            'fix': 'Add sources for factual claims'
        })

    base_score = cited_ratio * 100
    final_score = min(100, base_score + tier_bonus)

    # Identify uncited claims
    if cited_ratio < 0.9:
        issues.append({
            'metric': 'groundedness',
            'priority': 'P1',
            'location': 'general',
            'issue': f'Only {len(citations)}/{len(claims)} claims cited',
            'fix': 'Add citations for remaining claims'
        })

    return int(final_score), issues


def score_relevance(content: str) -> tuple[int, List[Dict[str, Any]]]:
    """Score relevance (0-100) - simplified heuristic."""
    # This is a simplified version - real implementation would use topic modeling

    paragraphs = content.split('\n\n')
    issues = []

    # Check for filler content (very short paragraphs, generic phrases)
    filler_phrases = [
        'in conclusion',
        'to summarize',
        'as we can see',
        'it goes without saying'
    ]

    filler_count = sum(1 for para in paragraphs if any(phrase in para.lower() for phrase in filler_phrases))

    if filler_count > len(paragraphs) * 0.2:
        issues.append({
            'metric': 'relevance',
            'priority': 'P2',
            'location': 'general',
            'issue': 'Filler content detected',
            'fix': 'Remove unnecessary transitional paragraphs'
        })

    # Rough heuristic
    score = max(70, 100 - (filler_count * 5))

    return score, issues


def score_readability(content: str, persona: str = 'strategic') -> tuple[int, List[Dict[str, Any]]]:
    """Score readability (0-100) based on sentence/paragraph length."""
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    issues = []

    if not sentences:
        return 0, [{'metric': 'readability', 'priority': 'P0', 'issue': 'No content'}]

    # Calculate averages
    avg_words_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences)
    avg_sentences_per_para = len(sentences) / max(1, len(paragraphs))

    # Persona-specific targets
    if persona == 'strategic':
        # Target: <15 words/sentence, <4 sentences/paragraph
        sentence_score = 100 if avg_words_per_sentence <= 15 else max(0, 100 - (avg_words_per_sentence - 15) * 5)
        para_score = 100 if avg_sentences_per_para <= 4 else max(0, 100 - (avg_sentences_per_para - 4) * 10)

        if avg_words_per_sentence > 15:
            issues.append({
                'metric': 'readability',
                'priority': 'P1',
                'location': 'general',
                'issue': f'Average sentence length {avg_words_per_sentence:.1f} words (target: ≤15)',
                'fix': 'Break long sentences into shorter ones'
            })

        if avg_sentences_per_para > 4:
            issues.append({
                'metric': 'readability',
                'priority': 'P1',
                'location': 'general',
                'issue': f'Average {avg_sentences_per_para:.1f} sentences/paragraph (target: ≤4)',
                'fix': 'Break long paragraphs into smaller sections'
            })

    else:  # hank_green or other personas
        # More flexible
        sentence_score = 100 if 10 <= avg_words_per_sentence <= 20 else 80
        para_score = 100 if 3 <= avg_sentences_per_para <= 6 else 80

    # Check for passive voice (simplified)
    passive_indicators = [' was ', ' were ', ' been ', ' being ']
    passive_count = sum(content.lower().count(ind) for ind in passive_indicators)
    passive_ratio = passive_count / len(sentences)

    if persona == 'strategic' and passive_ratio > 0.1:
        issues.append({
            'metric': 'readability',
            'priority': 'P1',
            'location': 'general',
            'issue': f'Passive voice detected ({passive_count} instances)',
            'fix': 'Convert to active voice'
        })

    final_score = (sentence_score + para_score) / 2

    return int(final_score), issues


def score_voice(content: str, persona: str = 'strategic') -> tuple[int, List[Dict[str, Any]]]:
    """Score voice consistency (0-100) based on persona patterns."""
    issues = []

    # AI tells - universally avoid
    ai_tells = [
        "it's important to note",
        "in today's landscape",
        "as discussed",
        "delve into",
        "comprehensive analysis"
    ]

    for tell in ai_tells:
        if tell in content.lower():
            issues.append({
                'metric': 'voice',
                'priority': 'P1',
                'location': 'general',
                'issue': f"AI tell detected: '{tell}'",
                'fix': 'Remove or rephrase more naturally'
            })

    # Corporate speak - Travis avoids
    corporate_speak = [
        'leverage',
        'synergy',
        'alignment',
        'stakeholder',
        'robust solution',
        'strategic imperatives'
    ]

    for phrase in corporate_speak:
        if phrase in content.lower():
            issues.append({
                'metric': 'voice',
                'priority': 'P1',
                'location': 'general',
                'issue': f"Corporate speak detected: '{phrase}'",
                'fix': 'Replace with concrete language'
            })

    # Hedging (for strategic persona)
    if persona == 'strategic':
        hedges = ['might', 'could', 'possibly', 'one might argue']
        for hedge in hedges:
            if hedge in content.lower():
                issues.append({
                    'metric': 'voice',
                    'priority': 'P1',
                    'location': 'general',
                    'issue': f"Hedging detected: '{hedge}'",
                    'fix': 'State directly without qualifier'
                })

    # Calculate score (start at 100, deduct for issues)
    score = 100 - (len(issues) * 5)
    score = max(0, score)

    return score, issues


def score_originality(content: str) -> tuple[int, List[Dict[str, Any]]]:
    """Score originality (0-100) based on clichés and specificity."""
    issues = []

    # Generic phrases
    generic_phrases = [
        'focus on what matters',
        'move fast and break things',
        'think outside the box',
        'at the end of the day',
        'game changer',
        'paradigm shift',
        'disruptive innovation'
    ]

    cliche_count = 0
    for phrase in generic_phrases:
        if phrase in content.lower():
            cliche_count += 1
            issues.append({
                'metric': 'originality',
                'priority': 'P2',
                'location': 'general',
                'issue': f"Generic phrase: '{phrase}'",
                'fix': 'Replace with specific insight or example'
            })

    # Check for specific numbers (good sign of originality)
    specific_numbers = len(re.findall(r'\b\d+[KMB]?\b', content))

    # Score calculation
    base_score = 80
    cliche_penalty = min(30, cliche_count * 10)
    specificity_bonus = min(20, specific_numbers * 2)

    final_score = base_score - cliche_penalty + specificity_bonus
    final_score = max(0, min(100, final_score))

    return int(final_score), issues


def get_recommendation(overall_score: int, issues: List[Dict]) -> str:
    """Determine recommendation based on score and issues."""
    p0_issues = [i for i in issues if i.get('priority') == 'P0']

    if p0_issues:
        return 'revise'

    if overall_score >= 85:
        return 'publish'
    elif overall_score >= 75:
        return 'revise'
    else:
        return 'needs_human_review'


def score_content(content: str, persona: str = 'strategic') -> Dict[str, Any]:
    """
    Score content on all 5 metrics.

    Args:
        content: Content to score
        persona: Persona to evaluate against (strategic, hank_green, how_to)

    Returns:
        Dict with scores, issues, and recommendation
    """
    all_issues = []

    # Score each metric
    groundedness, g_issues = score_groundedness(content)
    all_issues.extend(g_issues)

    relevance, r_issues = score_relevance(content)
    all_issues.extend(r_issues)

    readability, read_issues = score_readability(content, persona)
    all_issues.extend(read_issues)

    voice, v_issues = score_voice(content, persona)
    all_issues.extend(v_issues)

    originality, o_issues = score_originality(content)
    all_issues.extend(o_issues)

    # Calculate overall
    scores = {
        'groundedness': groundedness,
        'relevance': relevance,
        'readability': readability,
        'voice': voice,
        'originality': originality
    }

    overall = sum(scores.values()) / len(scores)

    recommendation = get_recommendation(int(overall), all_issues)

    return {
        'overall': int(overall),
        'scores': scores,
        'issues': all_issues,
        'recommendation': recommendation
    }


def main():
    parser = argparse.ArgumentParser(description='Score content quality')
    parser.add_argument('content_file', help='Path to content file')
    parser.add_argument('--persona', default='strategic',
                       choices=['strategic', 'hank_green', 'how_to'],
                       help='Persona to evaluate against')

    args = parser.parse_args()

    content_path = Path(args.content_file)

    if not content_path.exists():
        print(json.dumps({
            'error': f'File not found: {args.content_file}'
        }))
        sys.exit(1)

    try:
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = score_content(content, persona=args.persona)

        print(json.dumps(result, indent=2))

        # Exit with error code if needs revision
        if result['recommendation'] != 'publish':
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
