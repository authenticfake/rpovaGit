# REQ-002 Execution Guide

## Prerequisites

### System Requirements
- Python 3.11+
- pip package manager
- Git (for repository access)

### External Dependencies
- Kafka broker (for integration tests, optional for unit tests)
- Slack workspace with slash commands enabled (for manual testing)

### Environment Variables
```bash
export SLACK_SIGNING_SECRET="your_slack_signing_secret"
export KAFKA_BROKERS="localhost:9092"
export DATABASE_URL="postgresql://user:password@localhost:5432/coffeebuddy"
export PYTHONPATH="${PYTHONPATH}:${PWD}/runs/kit/REQ-002/src"
```

## Local Execution

### 1. Install Dependencies
```bash
cd /path/to/project
pip install -r runs/kit/REQ-002/requirements.txt
```

### 2. Run Unit Tests
```bash
# All tests
pytest runs/kit/REQ-002/test/test_coffee_command.py -v

# With coverage
pytest runs/kit/REQ-002/test/test_coffee_command.py --cov=runs.kit.REQ_002.src --cov-report=term-missing

# Specific test
pytest runs/kit/REQ-002/test/test_coffee_command.py::test_valid_signature_returns_modal -v
```

### 3. Lint Code
```bash
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test
```

### 4. Type Check
```bash
mypy --strict runs/kit/REQ-002/src
```

### 5. Security Scan
```bash
bandit -r runs/kit/REQ-002/src -f json -o reports/bandit-REQ-002.json
```

## CI/CD Integration

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    environment {
        SLACK_SIGNING_SECRET = credentials('slack-signing-secret')
        KAFKA_BROKERS = 'kafka-broker:9092'
        DATABASE_URL = credentials('database-url')
        PYTHONPATH = "${WORKSPACE}/runs/kit/REQ-002/src"
    }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-002/requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest runs/kit/REQ-002/test --junitxml=reports/junit-REQ-002.xml --cov-report=xml:reports/coverage-REQ-002.xml'
            }
        }
        stage('Lint') {
            steps {
                sh 'ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test'
            }
        }
        stage('Type Check') {
            steps {
                sh 'mypy --strict runs/kit/REQ-002/src'
            }
        }
    }
    post {
        always {
            junit 'reports/junit-REQ-002.xml'
            publishCoverage adapters: [coberturaAdapter('reports/coverage-REQ-002.xml')]
        }
    }
}
```

### GitHub Actions
```yaml
name: REQ-002 Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r runs/kit/REQ-002/requirements.txt
      - name: Run tests
        env:
          SLACK_SIGNING_SECRET: ${{ secrets.SLACK_SIGNING_SECRET }}
          KAFKA_BROKERS: localhost:9092
          DATABASE_URL: postgresql://user:password@localhost:5432/coffeebuddy
          PYTHONPATH: ${{ github.workspace }}/runs/kit/REQ-002/src
        run: pytest runs/kit/REQ-002/test --junitxml=reports/junit-REQ-002.xml
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: reports/junit-REQ-002