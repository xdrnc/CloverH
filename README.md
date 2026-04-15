# Engineering Interview

This application is an ADT (Admit/Discharge/Transfer) feed viewer. It ingests HL7 ADT messages, stores them in PostgreSQL, and displays patient event timelines in a React frontend.

During your live interview you will be asked several tasks to improve this application.  You can, and are encouraged to use Claude Code, during the interview process.  We want to see how you use AI and leverage it appropriately when building applications.

Please make sure this is set up and running prior to your interview. If you have any questions please reach out to the recruiter before the interview.

---

## Prerequisites

### Install uv (Python package manager)

uv is a fast Python package manager. On macOS:

```bash
brew install uv
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for other platforms.

### Install Podman

Podman is a container engine (similar to Docker). On macOS:

```bash
brew install podman
podman machine init
podman machine start
```

For other platforms, see the [Podman installation docs](https://podman.io/docs/installation).

### Install podman-compose

podman-compose orchestrates multi-container applications (like docker-compose, but for Podman):

```bash
uv tool install podman-compose
```

### Install Claude Code

You will need a Claude Code Platform Account (different than a normal Claude account).

1. **Get an API key**: Set up an account and create an API key at https://platform.claude.com/settings/keys
2. **Add credits**: We will reimburse you up to $50 USD for API key usage during your interview. Buy credits at https://platform.claude.com/settings/billing
3. **Install Claude Code**: Follow the instructions at https://code.claude.com/docs/en/quickstart
4. **Verify it works**: Run `ANTHROPIC_API_KEY=<your key> claude` to confirm Claude Code is working

Please make sure Claude Code is working before the interview and let your recruiter know if it is not ahead of time.

## Getting Started

### 1. Start the application

```bash
podman-compose down -v && podman-compose up --build
```

This starts three services:

| Service  | URL                    | Description          |
|----------|------------------------|----------------------|
| Frontend | http://localhost:3000   | React UI             |
| Backend  | http://localhost:8000   | FastAPI REST API     |
| Database | localhost:5432         | PostgreSQL 16        |

### 2. Load the ADT data

Load the sample ADT messages into the database:

```bash
podman-compose exec backend uv run python ingest.py /sample_data/adt_feeds.hl7
```

This is a batch process and will load a sample selection of fake healthcare data into the app.

### 3. Start Claude Code

In a separate terminal:

```bash
ANTHROPIC_API_KEY=<your key> claude
```

### 4. Use the app

Open http://localhost:3000 to view the ADT feed data.

## Stopping the application

```bash
podman-compose down
```

To also wipe the database volume:

```bash
podman-compose down -v
```

## Project Structure

```
├── backend/
│   ├── app.py              # FastAPI application and API routes
│   ├── models.py           # SQLAlchemy models (Patient, ADTEvent)
│   ├── database.py         # Database connection setup
│   ├── hl7_parser.py       # HL7 v2.x message parser
│   ├── ingest.py           # CLI ingestion script
│   ├── pyproject.toml      # Python dependencies (managed by uv)
│   └── Containerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main React component
│   │   ├── main.jsx        # Entry point
│   │   └── index.css       # Styles
│   ├── vite.config.js      # Vite config with API proxy
│   ├── package.json
│   └── Containerfile
├── sample_data/
│   ├── adt_feeds.hl7       # Sample HL7 ADT messages
│   └── claims.csv          # Sample institutional claims
└── docker-compose.yml      # podman-compose orchestration
```

## API Endpoints

- `GET /api/patients` — List all patients with ADT events
- `GET /api/patients/{mrn}/events` — Get ADT events for a patient (newest first)
