# llmail
# 🐳 Email AI Bots - Docker Test Environment

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository>
   cd email-ai-bots-docker
   ```

2. **Build and run tests**
   ```bash
   make test
   ```

3. **View results**
   ```bash
   make report        # Open HTML test report
   make logs          # View logs
   ```

## 📦 Architecture

The Docker environment consists of:

- **MailHog**: Test SMTP/IMAP server with Web UI
- **Dovecot**: IMAP server for email storage
- **Email Generator**: Creates test emails with various categories
- **Email Organizer Bot**: Categorizes and organizes emails
- **Email Responder Bot**: Generates AI responses to emails
- **Test Runner**: Automated test suite with coverage

## 🎯 Available Commands

```bash
make help          # Show all commands
make build         # Build Docker images
make up            # Start all services
make down          # Stop all services
make test          # Run full test suite
make test-quick    # Quick test without rebuild
make logs          # Show logs
make shell         # Open shell in test container
make clean         # Clean everything
make status        # Show service status
```

## 🧪 Testing Features

### Test Coverage
- Environment setup validation
- Email generation (multiple categories + spam)
- SMTP/IMAP connectivity
- Spam detection accuracy
- Email categorization
- Folder organization
- LLM model loading
- Response generation
- Draft creation
- Full workflow integration
- Performance metrics

### Test Reports
After running tests, find reports in:
- `test-results/report.html` - HTML test report
- `test-results/coverage/index.html` - Code coverage
- `test-results/junit.xml` - JUnit format
- `test-results/performance_metrics.json` - Performance data

## 📊 MailHog Web UI

Access the MailHog interface at: http://localhost:8025

Features:
- View all test emails
- Check spam detection
- Verify email organization
- Monitor SMTP traffic

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and adjust:

```bash
EMAIL_ADDRESS=test@localhost
EMAIL_PASSWORD=testpass123
MODEL_NAME=microsoft/DialoGPT-small
NUM_EMAILS=50
SPAM_RATIO=0.2
```

### Custom Test Data
Modify `generate_test_emails.py` to add:
- New email categories
- Custom spam patterns
- Different languages
- Attachment simulation

## 🐛 Troubleshooting

### Port conflicts
```bash
# Change ports in docker-compose.yml
ports:
  - "8026:8025"  # MailHog UI
  - "1026:1025"  # SMTP
```

### Memory issues
```bash
# Reduce model size or use mock mode
MODEL_NAME=microsoft/DialoGPT-small
```

### Clean start
```bash
make clean
make build
make test
```

## 📈 Performance

Typical test execution times:
- Environment setup: ~10s
- Email generation: ~5s
- Organization: ~10s
- Response generation: ~15s
- Full suite: ~60s

## 🔒 Security Notes

⚠️ **This is a TEST environment only!**
- Uses plain text passwords
- No SSL/TLS encryption
- Mock email addresses
- Simplified authentication

Never use in production!

## 📝 License

