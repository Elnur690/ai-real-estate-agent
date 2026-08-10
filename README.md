# 🏠 AI Real Estate Agent SaaS Platform

> **Automated Real Estate Matchmaking & Ingestion SaaS for Azerbaijan Agents**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)

---

## 📖 Complete Documentation
For full technical specifications, architecture diagrams, API endpoint reference, and feature matrices in 3 languages (English, Azerbaijani, Russian), see:

👉 **[DOCUMENTATION.md](file:///Users/nargiznuriyeva/Documents/ai-real-estate-agent/DOCUMENTATION.md)**

---

## ✨ Core Features At A Glance

- 🌐 **17 Real Estate Portal Crawlers + Telegram Channel Crawler**: Automated scrapers for `bina.az`, `tap.az`, `yeniemlak.az`, `evonline.az`, `ev10.az`, `vipemlak.az`, `ofis.az`, `kub.az`, `lalafo.az`, `homdom.az`, `rahatemlak.az`, `unvan.az`, `ipoteka.az`, `binam.az`, `binalar.az`, `mulk.az`, `villa.az`, and Telethon public channel monitors.
- 🏠 **"Sahibindən" (Direct Owner) Detection**: Automatic classification filtering out agency listings.
- 🤖 **Multi-LLM AI Engine**: Integrated adapters for **Google Gemini**, **Anthropic Claude**, and **OpenAI GPT** with Azerbaijani natural language search parsing.
- 💬 **Shared WhatsApp & Telegram Bot**: Onboarding, search management, channel toggling, and one-click listing reactions (`Maraqlanıram`, `Keç`, `Satılıb`).
- 🖥️ **React Admin Dashboard**: Real-time management of tenants, cash payments, AI provider routing, runtime settings, and scraper health.
- 💾 **Backup-as-a-Service (BaaS)**: Automated daily/weekly/monthly tenant data exports & full database compressed snapshots.

---

## ⚡ Quick Start (Docker Compose)

```bash
# 1. Clone Repository
git clone https://github.com/Elnur690/ai-real-estate-agent.git
cd ai-real-estate-agent

# 2. Configure Environment Variables
cp .env.example backend/.env

# 3. Launch Multi-container Stack
docker-compose up --build -d
```

- 🖥️ **Admin Dashboard**: `http://localhost:3000`
- ⚡ **FastAPI Swagger API**: `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Run Pytest suite
PYTHONPATH=backend ./backend/venv/bin/pytest backend/tests
```

---

## 📄 License
This project is licensed under the MIT License.
