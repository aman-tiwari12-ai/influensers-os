"""
Influencer OS — Real-Time Indian Micro-Influencer Discovery & Outreach System
CLI entry point

Usage:
    python main.py --keyword "olympiad preparation India" \
                   --category education \
                   --brand "SPARK Olympiads — competitive learning platform" \
                   --min-score 70 \
                   --send-outreach
"""

import argparse
import asyncio
import json
from src.automation.pipeline import run_full_pipeline

def main():
    parser = argparse.ArgumentParser(description='Influencer OS — discover and outreach Indian micro-influencers')
    parser.add_argument('--keyword', required=True, help='Discovery keyword (e.g. "olympiad preparation India")')
    parser.add_argument('--category', required=True,
                        choices=['education', 'beauty', 'finance', 'lifestyle', 'health'],
                        help='Brand category for segmentation and fit scoring')
    parser.add_argument('--brand', required=True, help='Brand description for outreach context')
    parser.add_argument('--brand-name', help='Brand name (defaults to first word of --brand)')
    parser.add_argument('--min-score', type=int, default=70, help='Minimum brand-fit score to include (0-100)')
    parser.add_argument('--send-outreach', action='store_true', help='Send email + DM to qualified creators')
    parser.add_argument('--output', default='output.json', help='Save results to JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Generate messages but do not send')
    args = parser.parse_args()

    brand_name = args.brand_name or args.brand.split()[0]

    brand_context = {
        'category':    args.category,
        'name':        brand_name,
        'description': args.brand,
        'keywords':    args.keyword.split(),
        'min_score':   args.min_score,
    }

    print(f"\n🔍 Influencer OS — starting discovery")
    print(f"   Keyword:  {args.keyword}")
    print(f"   Category: {args.category}")
    print(f"   Brand:    {args.brand}")
    print(f"   Min score: {args.min_score}/100\n")

    result = asyncio.run(run_full_pipeline(
        keyword=args.keyword,
        brand_context=brand_context,
        send_outreach=args.send_outreach and not args.dry_run
    ))

    print(f"\n✅ Pipeline complete")
    print(f"   Discovered:  {result['discovered']} creators")
    print(f"   Filtered:    {result['filtered']} passed filters")
    print(f"   Scored ≥{args.min_score}: {len([c for c in result['creators'] if c['brand_fit_score'] >= args.min_score])}")
    print(f"   Outreached:  {result['outreached']}")

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n📄 Results saved to {args.output}")

if __name__ == '__main__':
    main()
