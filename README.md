# Zed CV

AI-powered job matching platform for Zambia.

## Overview

Zed CV helps Zambian job seekers find the perfect roles using advanced AI matching. It analyzes CVs against local job listings, provides match scores, generates tailored cover letters, and delivers notifications directly via WhatsApp.

## Features

- **AI Job Matching**: Hybrid scoring based on vector similarity and skill overlap.
- **WhatsApp Integration**: Receive job alerts and interact with the platform via WhatsApp.
- **CV & Cover Letter Generation**: Professionally tailored documents using AI.
- **Mobile Money Support**: Seamless payments via MTN and Airtel (DPO Pay).

## Tech Stack

- **Frontend**: Next.js 14, Tailwind CSS, Vercel
- **Backend**: FastAPI, Docker, Oracle Cloud
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI**: Gemini (Embeddings), Gemini Flash 2.0 (LLM)
- **Automation**: n8n, WAHA (WhatsApp Gateway)

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker (for local development)

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

### Backend

```bash
cd apps/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## Deployment

Refer to [DEPLOY.md](DEPLOY.md) for detailed deployment instructions on Oracle Cloud and Vercel.

## License

Private / All Rights Reserved
