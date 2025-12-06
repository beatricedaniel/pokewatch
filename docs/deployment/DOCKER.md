# Docker Setup Guide

This guide explains how to build and run the PokeWatch API using Docker.

## Prerequisites

- Docker installed and running
- Docker Compose installed (or use `docker compose` command)

## Quick Start

### Using the setup script (recommended)

```bash
# Build images and start API
./setup.sh up

# Run tests
./setup.sh test

# Stop services
./setup.sh down

# View logs
./setup.sh logs

# Clean up everything
./setup.sh cleanup
```

### Manual Docker commands

#### Build the image

```bash
docker build -f docker/api.Dockerfile -t pokewatch-api .
```

#### Run the container

```bash
docker run -p 8000:8000 \
  -e POKEMON_PRICE_API_KEY=your_api_key_here \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data/processed:/app/data/processed:ro \
  pokewatch-api
```

#### Using docker-compose

```bash
# Start API service
docker-compose up -d api

# Run tests
docker-compose --profile test run --rm tests

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Setup Script Commands

The `setup.sh` script provides convenient commands:

| Command | Description |
|---------|-------------|
| `build` | Build Docker images only |
| `up` | Build and start API service |
| `down` | Stop all services |
| `test` | Run all tests (unit + integration) |
| `logs` | Show API logs |
| `cleanup` | Remove all containers and images |

## Environment Variables

Create a `.env` file in the project root:

```bash
POKEMON_PRICE_API_KEY=your_api_key_here
ENV=prod
LOG_LEVEL=INFO
```

Or set them when running:

```bash
export POKEMON_PRICE_API_KEY=your_api_key_here
./setup.sh up
```

## Logs

Logs are written to:
- **Console**: Standard output
- **File**: `logs/logs.txt` (appended, not overwritten)

The logs directory is mounted as a volume, so logs persist on the host machine.

## Testing

The test service runs both unit and integration tests:

```bash
./setup.sh test
```

Test results and logs are saved to `logs/logs.txt`.

## Health Check

The API includes a health check endpoint that Docker uses:

```bash
# Check health from host
curl http://localhost:8000/health
```

## Troubleshooting

### Container won't start

1. Check if port 8000 is already in use:
   ```bash
   lsof -i :8000
   ```

2. Check container logs:
   ```bash
   docker-compose logs api
   ```

3. Verify environment variables are set:
   ```bash
   docker-compose config
   ```

### Model not loading

1. Ensure processed data exists:
   ```bash
   ls -la data/processed/
   ```

2. Check if the data file matches the set name in `config/cards.yaml`

3. Verify the data file is readable:
   ```bash
   docker-compose exec api python -c "import pandas as pd; pd.read_parquet('/app/data/processed/sv2a_pokemon_card_151.parquet')"
   ```

### Tests failing

1. Ensure API is running before tests:
   ```bash
   docker-compose up -d api
   ```

2. Wait for API to be ready:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check test logs:
   ```bash
   cat logs/logs.txt
   ```

## Production Considerations

For production deployment:

1. **Use specific image tags** instead of `latest`
2. **Set up proper secrets management** (don't use .env files)
3. **Configure resource limits** in docker-compose.yml
4. **Set up log rotation** for logs/logs.txt
5. **Use a reverse proxy** (nginx, traefik) in front of the API
6. **Enable HTTPS** using TLS certificates

## File Structure

```
pokewatch/
├── docker/
│   └── api.Dockerfile          # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
├── setup.sh                    # Setup script
├── requirements.txt            # Python dependencies
├── logs/
│   └── logs.txt                # Application logs
└── data/
    └── processed/              # Processed data (snapshot in image)
```
