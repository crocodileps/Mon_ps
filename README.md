# 🎯 Mon_PS - Trading Platform for Sports Betting

**Quantitative sports betting trading platform combining automated ("Ligne") and manual ("Tabac") betting strategies.**

## 🚀 Quick Start

### Access
- **Dashboard**: http://91.98.131.218:3001/dashboard
- **Backend API**: http://localhost:8001 (VPN only)
- **Grafana**: http://localhost:3005

### Start Services
```bash
cd /home/Mon_ps/monitoring
docker compose up -d
```

## 📚 Documentation

**Complete documentation in `.docs/` folder:**

- **[STATUS.md](.docs/STATUS.md)** - Current project state (what works, what's TODO)
- **[METHODOLOGY.md](.docs/METHODOLOGY.md)** - Development methodology & best practices
- **[ARCHITECTURE.md](.docs/ARCHITECTURE.md)** - Technical architecture & structure
- **[TROUBLESHOOTING.md](.docs/TROUBLESHOOTING.md)** - Common issues & solutions
- **[TODO.md](.docs/TODO.md)** - Roadmap & next steps

## ✅ Current State (14 Nov 2025)

### Working
- ✅ Backend 100% operational (FastAPI, 18 endpoints)
- ✅ Frontend Dashboard functional at `/dashboard`
- ✅ PostgreSQL + TimescaleDB (400k+ odds entries)
- ✅ Monitoring: Grafana + Prometheus
- ✅ Security: WireGuard VPN access only

### In Progress
- ⚠️ Additional pages: /compare-agents, /analytics, /settings
- ⚠️ ML Agents optimization
- ⚠️ Mobile responsive design

## 🔧 Tech Stack

- **Backend**: FastAPI + PostgreSQL + TimescaleDB
- **Frontend**: Next.js 14 + React + TypeScript + Tailwind CSS
- **Infrastructure**: Docker + Hetzner CCX23
- **Monitoring**: Grafana + Prometheus

## 📝 Development Rules

1. **Never commit broken code**
2. **Git bisect for debugging**
3. **Documentation in sync with code**
4. **Backup before major changes**
5. **One problem = one focused commit**

## 🎓 Methodology

**Scientific & Methodical Approach:**
- Analyze before action
- Test every hypothesis
- Git bisect to find stable state
- Quality over speed ("Qualitative not rapid")

Read [METHODOLOGY.md](.docs/METHODOLOGY.md) for details.

## 👤 Author

Mya - [karouche.myriam@gmail.com](mailto:karouche.myriam@gmail.com)

## 📄 License

Private project - All rights reserved
