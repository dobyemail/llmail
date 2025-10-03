#!/bin/bash
# ============================================
# Email AI Bots - Automated Docker Test Suite
# One-click script to run complete tests
# ============================================

set -e  # Exit on error

# Kolory dla ładnego output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                          ║"
    echo "║         📧 EMAIL AI BOTS - DOCKER TEST SUITE 🤖         ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Funkcja do wyświetlania kroków
step() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Sprawdź wymagania
check_requirements() {
    step "Checking requirements..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed!"
        echo "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    success "Docker found: $(docker --version)"
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed!"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    success "Docker Compose found: $(docker-compose --version)"
    
    # Sprawdź czy Docker działa
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running!"
        echo "Please start Docker Desktop or Docker service"
        exit 1
    fi
    success "Docker daemon is running"
}

# Utwórz strukturę katalogów
create_directories() {
    step "Creating directory structure..."
    
    directories=(
        "dovecot"
        "logs"
        "reports"
        "test-results"
        "models"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        info "Created: $dir/"
    done
    
    success "Directory structure created"
}

# Zapisz pliki konfiguracyjne
create_config_files() {
    step "Creating configuration files..."
    
    # Utwórz .env jeśli nie istnieje
    if [ ! -f .env ]; then
        cat > .env << 'EOF'
# Email Configuration
EMAIL_ADDRESS=test@localhost
EMAIL_PASSWORD=testpass123

# Server Configuration
IMAP_SERVER=dovecot
SMTP_SERVER=mailhog
IMAP_PORT=143
SMTP_PORT=1025

# Model Configuration
MODEL_NAME=microsoft/DialoGPT-small
DEVICE=cpu

# Test Configuration
NUM_EMAILS=50
SPAM_RATIO=0.2
TEST_LIMIT=10

# Paths
MODELS_PATH=./models
LOGS_PATH=./logs
REPORTS_PATH=./reports
EOF
        info "Created .env file"
    fi
    
    # Dovecot config
    cat > dovecot/dovecot.conf << 'EOF'
protocols = imap
listen = *

mail_location = maildir:/var/mail/%u/Maildir

auth_mechanisms = plain login

passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}

userdb {
  driver = static
  args = uid=1000 gid=1000 home=/var/mail/%u
}

service imap-login {
  inet_listener imap {
    port = 143
  }
}

ssl = no
log_path = /dev/stderr
EOF
    
    # Dovecot users
    cat > dovecot/users << 'EOF'
test@localhost:{PLAIN}testpass123:1000:1000::/var/mail/test::
EOF
    
    success "Configuration files created"
}

# Wyczyść poprzednie kontenery
cleanup_old() {
    step "Cleaning up old containers..."
    
    docker-compose down -v 2>/dev/null || true
    
    # Usuń stare kontenery testowe
    docker ps -a | grep "email-" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
    
    success "Cleanup completed"
}

# Zbuduj obrazy
build_images() {
    step "Building Docker images..."
    
    docker-compose build --parallel
    
    success "Docker images built"
}

# Uruchom serwisy podstawowe
start_services() {
    step "Starting base services..."
    
    # Uruchom MailHog i Dovecot
    docker-compose up -d mailhog dovecot
    
    # Czekaj na gotowość
    info "Waiting for services to be ready..."
    sleep 5
    
    # Sprawdź czy serwisy działają
    if ! docker-compose ps | grep -q "mailhog.*Up"; then
        error "MailHog failed to start!"
        docker-compose logs mailhog
        exit 1
    fi
    
    if ! docker-compose ps | grep -q "dovecot.*Up"; then
        error "Dovecot failed to start!"
        docker-compose logs dovecot
        exit 1
    fi
    
    success "Services are running"
    info "MailHog UI available at: http://localhost:8025"
}

# Generuj testowe emaile
generate_emails() {
    step "Generating test emails..."
    
    docker-compose run --rm email-generator
    
    success "Test emails generated"
}

# Testuj organizera
test_organizer() {
    step "Testing Email Organizer Bot..."
    
    docker-compose run --rm email-organizer
    
    success "Email Organizer test completed"
}

# Testuj respondera
test_responder() {
    step "Testing Email Responder Bot..."
    
    docker-compose run --rm email-responder
    
    success "Email Responder test completed"
}

# Uruchom pełny test suite
run_test_suite() {
    step "Running complete test suite..."
    
    docker-compose run --rm test-runner
    
    success "Test suite completed"
}

# Generuj raport
generate_report() {
    step "Generating test reports..."
    
    if [ -f test-results/report.html ]; then
        success "Test report available at: test-results/report.html"
        
        # Spróbuj otworzyć w przeglądarce
        if command -v xdg-open &> /dev/null; then
            xdg-open test-results/report.html 2>/dev/null || true
        elif command -v open &> /dev/null; then
            open test-results/report.html 2>/dev/null || true
        fi
    fi
    
    if [ -f test-results/coverage/index.html ]; then
        info "Coverage report: test-results/coverage/index.html"
    fi
    
    if [ -f test-results/performance_metrics.json ]; then
        info "Performance metrics saved"
        cat test-results/performance_metrics.json | python -m json.tool
    fi
}

# Pokaż podsumowanie
show_summary() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    ✅ TESTS COMPLETED!                     ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    
    echo -e "\n${WHITE}📊 Results:${NC}"
    echo -e "  ${BLUE}•${NC} Test Report: ${YELLOW}test-results/report.html${NC}"
    echo -e "  ${BLUE}•${NC} Coverage: ${YELLOW}test-results/coverage/index.html${NC}"
    echo -e "  ${BLUE}•${NC} Logs: ${YELLOW}logs/${NC}"
    
    echo -e "\n${WHITE}🌐 Services:${NC}"
    echo -e "  ${BLUE}•${NC} MailHog UI: ${YELLOW}http://localhost:8025${NC}"
    
    echo -e "\n${WHITE}🛠️  Useful commands:${NC}"
    echo -e "  ${BLUE}•${NC} View logs: ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  ${BLUE}•${NC} Stop services: ${YELLOW}docker-compose down${NC}"
    echo -e "  ${BLUE}•${NC} Clean everything: ${YELLOW}docker-compose down -v${NC}"
    
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

# Obsługa błędów
trap 'error "Test failed! Check logs: docker-compose logs"' ERR

# Główna funkcja
main() {
    print_banner
    
    # Parsuj argumenty
    SKIP_BUILD=false
    QUICK_TEST=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --quick)
                QUICK_TEST=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build    Skip Docker image building"
                echo "  --quick         Run quick tests only"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Wykonaj kroki
    check_requirements
    create_directories
    create_config_files
    cleanup_old
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    fi
    
    start_services
    
    if [ "$QUICK_TEST" = false ]; then
        generate_emails
        sleep 2
        test_organizer
        sleep 2
        test_responder
        sleep 2
    fi
    
    run_test_suite
    generate_report
    show_summary
    
    # Zapytaj czy zostawić serwisy uruchomione
    echo -e "${YELLOW}Keep services running for manual testing? (y/n)${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        step "Stopping services..."
        docker-compose down
        success "Services stopped"
    else
        info "Services are still running. Use 'docker-compose down' to stop them."
    fi
}

# Uruchom
main "$@"