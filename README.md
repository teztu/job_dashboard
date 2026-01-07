# Job Hunter

AI-powered job hunting assistant for the Norwegian job market. Automatically scrapes job listings from Finn.no and Arbeidsplassen.no, tracks your applications, and provides insights to optimize your job search.

## Features

- **Automated Job Scraping** - Daily scraping of Norwegian job sites (Finn.no, Arbeidsplassen.no)
- **Smart Dashboard** - Streamlit-based UI for browsing jobs and tracking applications
- **Application Tracking** - Kanban-style board to track your job application pipeline
- **Analytics & Insights** - See which keywords work best, identify top hiring companies
- **Email Notifications** - Get daily digests of new matching jobs
- **GitHub Actions** - Fully automated daily scraping via CI/CD

## Screenshots

*Coming soon*

## Installation

### Prerequisites
- Python 3.11 or higher
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/teztu/job_dashboard.git
cd job_dashboard
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Copy the environment file and configure:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Usage

### CLI Commands

```bash
# Scrape all configured job sites
job-hunter scrape --all

# Scrape a specific site
job-hunter scrape --site finn

# List recent jobs
job-hunter list

# Show statistics
job-hunter stats

# Launch the dashboard
job-hunter dashboard
```

### Dashboard

Launch the interactive dashboard:
```bash
job-hunter dashboard
# or directly with streamlit
streamlit run src/dashboard/app.py
```

The dashboard provides:
- **Jobs** - Browse and filter all scraped jobs
- **Applications** - Track your application status (New → Interested → Applied → Interview → Offer)
- **Analytics** - Charts and insights about the job market

## Configuration

Edit `.env` to customize your search:

```env
# Search settings
SEARCH_LOCATION=Oslo
SEARCH_KEYWORDS=Junior utvikler,Python utvikler,Backend utvikler,Dataanalytiker

# Email notifications (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
```

## Project Structure

```
job-hunter/
├── src/
│   ├── scrapers/        # Job site scrapers
│   ├── database/        # SQLAlchemy models
│   ├── analytics/       # Statistics and insights
│   ├── notifications/   # Email notifications
│   ├── dashboard/       # Streamlit UI
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── .github/workflows/   # CI/CD pipelines
└── requirements.txt     # Dependencies
```

## Development

### Running Tests
```bash
pytest
```

### Linting
```bash
ruff check src/ tests/
```

## Roadmap

### MVP (Complete!)
- [x] Project setup with GitHub workflows
- [x] Database models (Job, Application, SearchKeyword)
- [x] Finn.no scraper
- [x] Arbeidsplassen.no scraper
- [x] Streamlit dashboard
- [x] CLI interface
- [x] Daily automation via GitHub Actions

### Future: AI Features
- [ ] AI job matching (score jobs against your profile)
- [ ] Auto-generate tailored CVs
- [ ] Auto-generate cover letters
- [ ] Smart recommendations

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with [Claude Code](https://claude.com/claude-code)
