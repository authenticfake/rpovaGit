# REQ-002 Execution HOWTO

## Prerequisites

### System Requirements
- Python 3.11+
- pip package manager
- Docker (optional, for Kafka integration tests)

### Environment Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r runs/kit/REQ-002/requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export SLACK_SIGNING_SECRET="test_signing_secret_12345"
   export KAFKA_BROKERS="localhost:9092"
   export PYTHONPATH="."
   ```

   Or create `.env` file:
   ```
   SLACK_SIGNING_SECRET=test_signing_secret_12345
   KAFKA_BROKERS=localhost:9092
   PYTHONPATH=.
   ```

### External Tools

- **Kafka (optional for integration tests):**
  ```bash
  docker run -d --name kafka \
    -p 9092:9092 \
    -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
    apache/kafka:latest
  ```

## Running Tests

### Unit Tests
```bash
pytest runs/kit/REQ-002/test/test_coffee_command.py -v --tb=short
```

### Integration Tests
```bash
pytest runs/kit/REQ-002/test/test_integration_slack_api.py -v --tb=short
```

### All Tests with Coverage
```bash
pytest runs/kit/REQ-002/test -v --cov=runs.kit.REQ_002.src --cov-report=xml:reports/coverage-REQ-002.xml --cov-report=term
```

### Lint
```bash
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test
```

### Type Check
```bash
mypy runs/kit/REQ-002/src --strict
```

## Running Locally

### Start FastAPI Server
```bash
uvicorn runs.kit.REQ_002.src.api.slack_routes:router --reload --host 0.0.0.0 --port 8000
```

### Test Endpoint with curl
```bash
curl -X POST http://localhost:8000/slack/commands/coffee \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Slack-Request-Timestamp: $(date +%s)" \
  -H "X-Slack-Signature: v0=test_signature" \
  -d "trigger_id=trigger_123&user_id=U123&channel_id=C123&team_id=T123&command=/coffee"
```

## Enterprise Runner Configuration

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    environment {
        SLACK_SIGNING_SECRET = credentials('slack-signing-secret')
        KAFKA_BROKERS = 'kafka.internal:9092'
    }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-002/requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest runs/kit/REQ-002/test -v --junitxml=reports/junit-REQ-002.xml'
            }
        }
        stage('Lint') {
            steps {
                sh 'ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test'
            }
        }
    }
    post {
        always {
            junit 'reports/junit-REQ-002.xml'
        }
    }
}
```

### SonarQube Integration
```bash
sonar-scanner \
  -Dsonar.projectKey=coffeebuddy-req-002 \
  -Dsonar.sources=runs/kit/REQ-002/src \
  -Dsonar.tests=runs/kit/REQ-002/test \
  -Dsonar.python.coverage.reportPaths=reports/coverage-REQ-002.xml
```

## Artifacts and Reports

- **JUnit XML:** `reports/junit-REQ-002.xml`
- **Coverage XML:** `reports/coverage-REQ-002.xml`
- **Coverage HTML:** `htmlcov/index.html` (run `pytest --cov-report=html`)

## Troubleshooting

### Import Path Issues

**Problem:** `ModuleNotFoundError: No module named 'runs'`

**Solution:**
```bash
export PYTHONPATH="."
# or
export