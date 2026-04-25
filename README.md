# 🇮🇳 Influencer OS — Real-Time Indian Micro-Influencer Discovery & Outreach System

> **Automated, keyword-driven influencer intelligence pipeline for Indian micro-creators (5K–100K followers). Zero paid databases. No hardcoded lists. AI-personalized outreach at scale.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Task-by-Task Breakdown](#task-by-task-breakdown)
- [Setup & Installation](#setup--installation)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Data Schema](#data-schema)
- [Sample Outputs](#sample-outputs)
- [Automation Layer](#automation-layer)
- [Collaboration Strategy Framework](#collaboration-strategy-framework)
- [Supported Categories](#supported-categories)
- [Tech Stack](#tech-stack)

---

## Overview

Influencer OS is a fully automated micro-influencer discovery and outreach system designed for Indian creators across Education, Beauty, Fintech, D2C Lifestyle, and Health & Wellness verticals.

**Key capabilities:**
- Real-time creator discovery via YouTube Data API v3 and Instagram Graph API
- Keyword-driven search — no hardcoded influencer lists
- Automated filtering by follower range, region, and activity
- Content context intelligence using transcript and caption analysis
- Dynamic brand-fit scoring per creator
- AI-generated personalized outreach (email + DM) via Claude Sonnet
- Programmatic outreach delivery via SendGrid/Brevo + Instagrapi

**Supported platforms:** YouTube · Instagram · LinkedIn (optional) · X/Twitter (optional)

**Follower range:** 5,000 – 100,000 (micro-influencer tier)

**Region:** India (enforced via `regionCode=IN` and geo-signals)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INFLUENCER OS PIPELINE                        │
└─────────────────────────────────────────────────────────────────────┘

  [1] KEYWORD INPUT
       │  Runtime keyword(s) + brand category
       ▼
  [2] CREATOR DISCOVERY ENGINE
       │  YouTube Data API v3  ──► search.list (keyword + regionCode=IN)
       │                       ──► channels.list (stats enrichment)
       │  Instagram Graph API  ──► /ig_hashtag_search
       │                       ──► /hashtag/{id}/top_media
       │                       ──► /{user-id}?fields=biography,followers_count
       ▼
  [3] FILTERING ENGINE
       │  • Follower range:  5K – 100K
       │  • Region:          India (language signals + geo tags)
       │  • Activity:        Last post within 30 days
       │  • Relevance:       Keyword-to-content cosine similarity > 0.6
       ▼
  [4] CONTENT CONTEXT INTELLIGENCE
       │  YouTube:  youtube-transcript-api → transcript text
       │            + video titles, descriptions, tags
       │  Instagram: caption text + hashtag array
       │  ──► Claude Sonnet classifies content themes
       │  ──► Segment assignment (A / B / C per category)
       ▼
  [5] PROFILE ENRICHMENT
       │  • follower_count, avg_views, engagement_rate
       │  • content_themes[], niche_classification, segment
       │  • contact_email (bio regex extraction)
       │  • brand_fit_score (0–100)
       │  • recommended_collab_type
       ▼
  [6] BRAND–CREATOR FIT SCORING
       │  • Keyword overlap score
       │  • Audience intent alignment
       │  • Engagement quality score
       │  • Content recency bonus
       │  ──► Weighted score 0–100
       ▼
  [7] OUTREACH PERSONALIZATION (Claude Sonnet)
       │  Input:  creator profile + content signals + brand context
       │  Output: Email pitch (60–90 words) + Instagram DM (15–30 words)
       │  Each message references: niche · recent content · collab value
       ▼
  [8] OUTREACH AUTOMATION
       │  Email:    Brevo API (300/day free) or Gmail SMTP OAuth2
       │  DM:       Instagrapi (Python) or Meta Graph API v18+ Messaging
       │  Tracking: Webhook callbacks for open/reply events
       ▼
  [9] COLLABORATION STRATEGY LAYER
       └─► Segment-mapped collab type recommendations per brand category
```

---

## Task-by-Task Breakdown

### Task 1 — Real-Time Influencer Discovery Engine

**No hardcoded lists. All creators discovered programmatically at runtime.**

#### YouTube Discovery
```python
# src/discovery/youtube_discovery.py

from googleapiclient.discovery import build

def discover_youtube_creators(keyword: str, max_results: int = 50) -> list:
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    # Step 1: Search videos by keyword with India region filter
    search_response = youtube.search().list(
        q=keyword,
        type='channel',
        regionCode='IN',
        relevanceLanguage='hi',   # Hindi-first, also returns English
        maxResults=max_results,
        part='snippet'
    ).execute()

    channel_ids = [item['snippet']['channelId'] for item in search_response['items']]

    # Step 2: Fetch channel statistics
    channels_response = youtube.channels().list(
        id=','.join(channel_ids),
        part='snippet,statistics,brandingSettings'
    ).execute()

    return channels_response['items']
```

#### Instagram Discovery
```python
# src/discovery/instagram_discovery.py

import requests

def discover_instagram_creators(hashtag: str, access_token: str) -> list:
    base = 'https://graph.facebook.com/v18.0'

    # Step 1: Resolve hashtag ID
    hashtag_resp = requests.get(f'{base}/ig_hashtag_search', params={
        'user_id': IG_BUSINESS_USER_ID,
        'q': hashtag,
        'access_token': access_token
    }).json()
    hashtag_id = hashtag_resp['data'][0]['id']

    # Step 2: Get top media for hashtag
    media_resp = requests.get(f'{base}/{hashtag_id}/top_media', params={
        'fields': 'id,owner,caption,like_count,comments_count,timestamp',
        'access_token': access_token
    }).json()

    # Step 3: Fetch creator profiles
    creators = []
    for post in media_resp['data']:
        user_id = post['owner']['id']
        profile = requests.get(f'{base}/{user_id}', params={
            'fields': 'username,biography,followers_count,media_count',
            'access_token': access_token
        }).json()
        creators.append({**profile, 'sample_post': post})

    return creators
```

---

### Task 2 — Automated Filtering & Classification

```python
# src/filtering/filter_engine.py

from datetime import datetime, timedelta

FILTER_CONFIG = {
    'min_followers': 5_000,
    'max_followers': 100_000,
    'region': 'India',
    'max_days_since_post': 30,
    'min_engagement_rate': 0.02,   # 2%
    'min_keyword_relevance': 0.6,
}

def filter_creators(creators: list, keyword: str) -> list:
    filtered = []
    for c in creators:
        followers = c.get('follower_count', 0)
        if not (FILTER_CONFIG['min_followers'] <= followers <= FILTER_CONFIG['max_followers']):
            continue
        if not is_india_based(c):
            continue
        if not posted_recently(c, FILTER_CONFIG['max_days_since_post']):
            continue
        if engagement_rate(c) < FILTER_CONFIG['min_engagement_rate']:
            continue
        c['relevance_score'] = keyword_relevance(c, keyword)
        if c['relevance_score'] >= FILTER_CONFIG['min_keyword_relevance']:
            filtered.append(c)

    return sorted(filtered, key=lambda x: x['relevance_score'], reverse=True)


def segment_creators(creators: list, category: str) -> dict:
    """Auto-segment into 3 clusters using content signals."""
    segments = {'A': [], 'B': [], 'C': []}
    thresholds = SEGMENT_THRESHOLDS[category]  # see config/segments.yaml

    for c in creators:
        themes = c.get('content_themes', [])
        if any(t in thresholds['A'] for t in themes):
            segments['A'].append(c)
        elif any(t in thresholds['B'] for t in themes):
            segments['B'].append(c)
        else:
            segments['C'].append(c)

    return segments
```

**Segment definitions (Education example):**

| Segment | Label | Content signals |
|---------|-------|-----------------|
| A | Olympiad preparation | `olympiad`, `IMO`, `NSO`, `SOF`, `competition math` |
| B | Reasoning & aptitude | `reasoning`, `aptitude`, `logical`, `NTSE`, `mental math` |
| C | Competition awareness | `student life`, `exam tips`, `motivation`, `study vlog` |

---

### Task 3 — Profile Enrichment Engine

```python
# src/enrichment/profile_enricher.py

import re

def enrich_creator(raw_creator: dict, platform: str) -> dict:
    return {
        'id':                  f"{platform}_{raw_creator['id']}",
        'platform':            platform,
        'handle':              raw_creator.get('username') or raw_creator.get('customUrl'),
        'profile_url':         build_profile_url(platform, raw_creator),
        'followers':           raw_creator.get('follower_count') or raw_creator.get('subscriberCount'),
        'avg_views':           calculate_avg_views(raw_creator),
        'engagement_rate':     calculate_engagement_rate(raw_creator),
        'region':              detect_region(raw_creator),
        'language':            detect_language(raw_creator),
        'last_post':           raw_creator.get('last_post_date'),
        'content_themes':      [],   # populated by content intelligence layer
        'niche_classification':'',   # populated by content intelligence layer
        'segment':             '',   # populated by filter engine
        'contact_email':       extract_email_from_bio(raw_creator.get('biography', '')),
        'brand_fit_score':     0,    # populated by fit scoring engine
        'recommended_collab':  '',   # populated by strategy layer
        'outreach_signals':    {}    # populated by content intelligence layer
    }

def extract_email_from_bio(bio: str) -> str:
    """Extract contact email from bio text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, bio)
    return matches[0] if matches else ''
```

---

### Task 4 — Content Context Intelligence Layer

```python
# src/enrichment/content_intelligence.py

from youtube_transcript_api import YouTubeTranscriptApi
import anthropic

client = anthropic.Anthropic()

def analyse_content_context(creator: dict, brand_category: str) -> dict:
    """Extract content signals from transcripts, captions, hashtags."""

    # Collect raw text signals
    text_signals = []

    if creator['platform'] == 'YouTube':
        for video_id in creator.get('recent_video_ids', [])[:5]:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
                text_signals.append(' '.join([t['text'] for t in transcript[:100]]))
            except:
                pass
        text_signals += creator.get('video_titles', [])
        text_signals += creator.get('video_descriptions', [])

    elif creator['platform'] == 'Instagram':
        text_signals += creator.get('recent_captions', [])
        text_signals += creator.get('hashtags', [])

    combined_text = ' '.join(text_signals)[:4000]

    # Claude classification
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=500,
        messages=[{
            'role': 'user',
            'content': f"""Analyse this creator's content for brand category: {brand_category}

Content signals:
{combined_text}

Return JSON only:
{{
  "content_themes": ["theme1", "theme2", "theme3"],
  "niche_classification": "single niche label",
  "primary_audience": "describe audience",
  "recent_content_signal": "most recent notable content topic",
  "brand_readiness": "high/medium/low"
}}"""
        }]
    )

    return json.loads(response.content[0].text)
```

---

### Task 5 — Brand–Creator Fit Matching Engine

```python
# src/enrichment/fit_scorer.py

SCORING_WEIGHTS = {
    'keyword_overlap':     0.35,
    'audience_intent':     0.25,
    'engagement_quality':  0.20,
    'content_recency':     0.10,
    'contact_available':   0.10,
}

BRAND_MAPPINGS = {
    'education': {
        'olympiad preparation': {'target_segment': 'A', 'collab': 'Product trial + Affiliate'},
        'reasoning skills':     {'target_segment': 'B', 'collab': 'Paid sponsorship'},
        'student motivation':   {'target_segment': 'C', 'collab': 'Barter + UGC'},
    },
    'beauty': {
        'skincare routine':     {'target_segment': 'A', 'collab': 'Product trial + Paid'},
        'makeup tutorial':      {'target_segment': 'B', 'collab': 'Barter + UGC'},
        'product review':       {'target_segment': 'C', 'collab': 'Affiliate + Paid review'},
    },
    'finance': {
        'SIP investing':        {'target_segment': 'A', 'collab': 'Affiliate + Sponsored'},
        'budgeting advice':     {'target_segment': 'B', 'collab': 'UGC + Barter'},
        'credit literacy':      {'target_segment': 'C', 'collab': 'Affiliate + Sponsored'},
    }
}

def score_brand_fit(creator: dict, brand_category: str, brand_keywords: list) -> dict:
    score = 0
    themes = creator.get('content_themes', [])

    # Keyword overlap
    overlap = len(set(themes) & set(brand_keywords)) / max(len(brand_keywords), 1)
    score += overlap * SCORING_WEIGHTS['keyword_overlap'] * 100

    # Engagement quality
    er = creator.get('engagement_rate', 0)
    score += min(er / 0.08, 1) * SCORING_WEIGHTS['engagement_quality'] * 100

    # Content recency
    days_since = days_since_last_post(creator)
    recency = max(0, 1 - days_since / 30)
    score += recency * SCORING_WEIGHTS['content_recency'] * 100

    # Contact availability
    if creator.get('contact_email'):
        score += SCORING_WEIGHTS['contact_available'] * 100

    creator['brand_fit_score'] = round(min(score, 100))
    creator['recommended_collab'] = get_collab_type(creator, brand_category)

    return creator
```

---

### Task 6 — Personalized Outreach Generator

```python
# src/outreach/message_generator.py

import anthropic

client = anthropic.Anthropic()

def generate_outreach(creator: dict, brand_context: str) -> dict:
    """
    Generate personalized email + DM using creator's content signals.
    No templates — each message is unique to the creator.
    """
    prompt = f"""You are an influencer marketing specialist for {brand_context}.

Creator profile:
- Name: {creator['name']}
- Platform: {creator['platform']}  
- Niche: {creator['niche_classification']}
- Content themes: {', '.join(creator['content_themes'])}
- Recent content: "{creator['outreach_signals'].get('recent_content_signal', '')}"
- Audience: {creator['outreach_signals'].get('primary_audience', 'Indian micro-influencer')}
- Followers: {creator['followers']:,}
- Brand-fit score: {creator['brand_fit_score']}/100

Generate personalized outreach. Return JSON only:
{{
  "email": "60-90 word email pitch referencing their niche, recent content theme, and specific collaboration value",
  "dm": "15-30 word Instagram DM referencing their topic and collaboration intent"
}}

Rules:
- Reference specific content signals, not generic phrases
- Mention the creator's audience relevance to the brand
- Email must have a clear collaboration ask
- DM must be conversational and concise
- No "Hi [Name]" placeholders — use actual name"""

    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}]
    )

    return json.loads(response.content[0].text)
```

---

### Task 7 — Outreach Automation Layer

#### Email Automation (Brevo — 300 emails/day free)
```python
# src/automation/email_sender.py

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def send_email_outreach(creator: dict, email_body: str, brand_name: str):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{'email': creator['contact_email'], 'name': creator['name']}],
        sender={'name': brand_name, 'email': SENDER_EMAIL},
        subject=f"Collaboration opportunity — {brand_name} x {creator['handle']}",
        text_content=email_body,
        tags=[creator['platform'], creator['segment'], brand_name]
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        log_outreach(creator, 'email', 'sent')
    except ApiException as e:
        log_outreach(creator, 'email', f'failed: {e}')
```

#### Instagram DM Automation (Instagrapi)
```python
# src/automation/instagram_dm.py

from instagrapi import Client

def send_instagram_dm(creator: dict, dm_text: str, session_file: str = 'session.json'):
    cl = Client()

    # Load existing session to avoid repeated logins
    try:
        cl.load_settings(session_file)
        cl.login(IG_USERNAME, IG_PASSWORD)
    except:
        cl.login(IG_USERNAME, IG_PASSWORD)
        cl.dump_settings(session_file)

    # Resolve username to user_id
    user_info = cl.user_info_by_username(creator['handle'].lstrip('@'))
    user_id = user_info.pk

    cl.direct_send(dm_text, user_ids=[user_id])
    log_outreach(creator, 'instagram_dm', 'sent')
```

#### Orchestration Pipeline
```python
# src/automation/pipeline.py

import asyncio
from typing import List

async def run_full_pipeline(keyword: str, brand_context: dict) -> dict:
    # 1. Discover
    yt_creators = discover_youtube_creators(keyword)
    ig_creators = discover_instagram_creators(keyword_to_hashtag(keyword))
    all_creators = yt_creators + ig_creators

    # 2. Filter & segment
    filtered = filter_creators(all_creators, keyword)
    segments = segment_creators(filtered, brand_context['category'])

    # 3. Enrich + analyse (parallel)
    enriched = await asyncio.gather(*[
        enrich_and_analyse(c, brand_context['category'])
        for c in filtered
    ])

    # 4. Score
    scored = [score_brand_fit(c, brand_context['category'], brand_context['keywords'])
              for c in enriched]

    # 5. Generate outreach for top creators (score >= 70)
    top_creators = [c for c in scored if c['brand_fit_score'] >= 70]
    for creator in top_creators:
        messages = generate_outreach(creator, brand_context['description'])
        creator['outreach_messages'] = messages

    # 6. Send outreach
    for creator in top_creators:
        if creator.get('contact_email'):
            send_email_outreach(creator, creator['outreach_messages']['email'],
                                brand_context['name'])
        send_instagram_dm(creator, creator['outreach_messages']['dm'])

    return {'discovered': len(all_creators), 'filtered': len(filtered),
            'outreached': len(top_creators), 'creators': scored}
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- YouTube Data API v3 key ([console.cloud.google.com](https://console.cloud.google.com))
- Meta Graph API access token (for Instagram)
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- Brevo account (free tier — [brevo.com](https://brevo.com))

### Install

```bash
git clone https://github.com/YOUR_USERNAME/influencer-os.git
cd influencer-os
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your keys
```

```env
# .env
YOUTUBE_API_KEY=your_youtube_data_api_v3_key
INSTAGRAM_ACCESS_TOKEN=your_meta_graph_api_token
IG_BUSINESS_USER_ID=your_ig_business_account_id
ANTHROPIC_API_KEY=your_anthropic_api_key
BREVO_API_KEY=your_brevo_api_key
SENDER_EMAIL=outreach@yourbrand.com
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password
```

---

## Usage Guide

### CLI — single run
```bash
python main.py \
  --keyword "olympiad preparation India" \
  --category education \
  --brand "SPARK Olympiads — competitive learning platform" \
  --min-score 70 \
  --send-outreach
```

### Python API
```python
from src.automation.pipeline import run_full_pipeline
import asyncio

result = asyncio.run(run_full_pipeline(
    keyword='skincare routine India',
    brand_context={
        'category': 'beauty',
        'name': 'Glow India',
        'description': 'Glow India — affordable skincare brand for Indian skin tones',
        'keywords': ['skincare', 'dermat tips', 'affordable beauty', 'SPF India']
    }
))

print(f"Discovered: {result['discovered']}")
print(f"Filtered:   {result['filtered']}")
print(f"Outreached: {result['outreached']}")
```

### Interactive Dashboard (prototype)
```bash
# Open index.html in browser — no server needed
open index.html
```

---

## Data Schema

Full enriched creator profile output:

```json
{
  "id": "yt_UC4xKdmAXFh4ACjc",
  "platform": "YouTube",
  "handle": "@MathWithPriya",
  "profile_url": "https://youtube.com/@MathWithPriya",
  "followers": 42800,
  "avg_views": 18400,
  "engagement_rate": 4.3,
  "region": "India",
  "language": "Hindi + English",
  "last_post": "2025-04-18",
  "content_themes": [
    "olympiad preparation",
    "CBSE math tricks",
    "reasoning skills"
  ],
  "niche_classification": "Olympiad educator",
  "segment": "A",
  "segment_label": "Olympiad preparation",
  "contact_email": "priya.teaches@gmail.com",
  "bio_extract": "Helping students crack IMO & NSO since 2019",
  "brand_fit_score": 91,
  "fit_reasoning": "High alignment — olympiad prep content matches assessment platform",
  "recommended_collab": "Product trial + Affiliate",
  "outreach_signals": {
    "recent_content_signal": "10 tricks for NSO class 7 mock test",
    "primary_audience": "Students age 10–16, competitive exam aspirants",
    "brand_readiness": "high"
  },
  "outreach_messages": {
    "email": "Hi Priya, your recent NSO class 7 preparation video showed exactly the focused approach SPARK Olympiad students need. Your community of 42K competitive learners is a natural fit for our adaptive assessment platform — we'd love to offer your audience a free trial. Could we explore an affiliate partnership this month?",
    "dm": "Hey Priya! Loved your NSO tricks video. We're building India's #1 olympiad prep platform — open to a collab for your students? 🎯"
  }
}
```

---

## Sample Outputs

### Sample Email (Education — Olympiad)

> **Subject:** Collaboration opportunity — SPARK Olympiads x @MathWithPriya
>
> Hi Priya, your recent NSO class 7 preparation video showcased exactly the structured, competition-ready approach our students at SPARK Olympiads need. With 42K followers deeply invested in competitive math, your audience is a natural fit for our adaptive olympiad practice platform. We'd love to offer your community an exclusive free trial and explore an affiliate partnership — would you be open to a quick call this week?

### Sample Instagram DM (Education — Olympiad)

> Hey Priya! Loved your NSO mock test tricks video 🎯 We're building India's top olympiad prep platform — open to a collab for your students?

### Sample Email (Beauty — Skincare)

> Hi Simran, your 5-step morning skincare routine video really resonated — recommending affordable products that actually work for Indian skin tones is exactly the trust Glow India is built on. Your 38K engaged followers would love our new SPF range, designed specifically for South Asian complexions. We'd like to send you a full trial kit — would a product review or reel collaboration work for you?

### Sample Instagram DM (Beauty — Skincare)

> Hey Simran! Your affordable skincare content is exactly what we love 🌟 We make SPF for Indian skin tones — open to a collab?

---

## Automation Layer

| Channel | Tool | Free Tier | Rate Limit |
|---------|------|-----------|------------|
| Email | Brevo | 300 emails/day | — |
| Email (alt) | Gmail SMTP + OAuth2 | 500/day | 100/hr |
| Instagram DM | Instagrapi (open source) | Unlimited | ~50–100/day safe |
| Instagram DM (alt) | Meta Graph API Messaging | Business accounts | Varies |
| Workflow | Python asyncio + cron | Free | — |
| Optional scheduler | Prefect Cloud | Free tier | — |

**Outreach tracking:**
- Email opens/clicks via Brevo webhook
- DM reply detection via Instagrapi session polling
- All events logged to SQLite (`outreach_log.db`)

---

## Collaboration Strategy Framework

### Education

| Segment | Creator type | Recommended strategy |
|---------|-------------|----------------------|
| A — Olympiad prep | IMO/NSO educators, competition math | Product trial + Affiliate |
| B — Reasoning & aptitude | Aptitude trainers, NTSE creators | Paid sponsorship + UGC |
| C — Competition awareness | Student vloggers, motivation creators | Barter + Affiliate |

### Beauty

| Segment | Creator type | Recommended strategy |
|---------|-------------|----------------------|
| A — Skincare educators | Dermat-advice, routine creators | Product trial + Paid sponsorship |
| B — Makeup tutorials | GRWM, bridal, daily makeup | Barter + UGC partnership |
| C — Product reviewers | Honest haul reviews, comparisons | Affiliate + Paid review |

### Fintech

| Segment | Creator type | Recommended strategy |
|---------|-------------|----------------------|
| A — Investing basics | SIP educators, mutual fund explainers | Affiliate + Paid sponsorship |
| B — Budgeting | Budget planning, frugal living | UGC + Barter |
| C — Credit literacy | Credit card reviewers, CIBIL tips | Affiliate + Paid sponsorship |

### D2C / Lifestyle

| Segment | Creator type | Recommended strategy |
|---------|-------------|----------------------|
| A — Sustainable living | Eco lifestyle, minimalist creators | Ambassador program + Barter |
| B — Home & decor | Interior styling, decor hauls | Product trial + UGC |
| C — Food & nutrition | Healthy meal prep, nutrition tips | Affiliate + Paid review |

---

## Supported Categories

| Category | Example keywords | Platform focus |
|----------|-----------------|----------------|
| Education | `olympiad preparation India`, `CBSE math tricks` | YouTube primary |
| Beauty | `skincare routine India`, `affordable makeup India` | Instagram primary |
| Fintech | `personal finance India`, `SIP investing basics` | YouTube + Instagram |
| D2C Lifestyle | `sustainable living India`, `home decor budget India` | Instagram primary |
| Health & Wellness | `yoga beginners India`, `Ayurveda tips Hindi` | YouTube + Instagram |

The system is **category-agnostic** — any keyword string works as runtime input.

---

## Tech Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Discovery — YouTube | YouTube Data API v3 | Free (10K units/day) |
| Discovery — Instagram | Meta Graph API v18+ | Free |
| Transcript extraction | `youtube-transcript-api` | Free / open source |
| Content intelligence | Claude Sonnet (`claude-sonnet-4-20250514`) | Pay per token |
| Outreach generation | Claude Sonnet | Pay per token |
| Email delivery | Brevo free tier | Free (300/day) |
| Instagram DM | Instagrapi | Free / open source |
| Language | Python 3.10+ | Free |
| Orchestration | asyncio + cron | Free |

**Zero paid influencer databases. Zero hardcoded creator lists.**

---

## Project Structure

```
influencer-os/
├── README.md
├── index.html                    # Interactive prototype dashboard
├── main.py                       # CLI entry point
├── requirements.txt
├── .env.example
├── config/
│   └── segments.yaml             # Segment keyword thresholds per category
├── src/
│   ├── discovery/
│   │   ├── youtube_discovery.py
│   │   └── instagram_discovery.py
│   ├── filtering/
│   │   └── filter_engine.py
│   ├── enrichment/
│   │   ├── profile_enricher.py
│   │   ├── content_intelligence.py
│   │   └── fit_scorer.py
│   ├── outreach/
│   │   └── message_generator.py
│   └── automation/
│       ├── email_sender.py
│       ├── instagram_dm.py
│       └── pipeline.py
├── examples/
│   ├── sample_creator_output.json
│   ├── sample_email_education.txt
│   ├── sample_dm_education.txt
│   └── sample_email_beauty.txt
└── docs/
    ├── architecture.md
    └── api_reference.md
```

---

## License

MIT — free to use, modify, and build on.

---

*Built for real-time Indian micro-influencer discovery at scale. No paid databases, no manual lists, no templates.*
