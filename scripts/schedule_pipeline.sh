#!/bin/bash
#
# Schedule PokeWatch ML Pipeline with cron
# Week 2, Day 5: Simple pipeline scheduling
#
# Usage:
#   ./scripts/schedule_pipeline.sh install   # Add cron job
#   ./scripts/schedule_pipeline.sh remove    # Remove cron job
#   ./scripts/schedule_pipeline.sh status    # Check if scheduled

set -e

# Get absolute path to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Pipeline command to run
PIPELINE_CMD="cd $PROJECT_ROOT && source .venv/bin/activate && python -m pipelines.ml_pipeline"

# Log file for cron output
LOG_FILE="$PROJECT_ROOT/logs/pipeline_cron.log"

# Cron schedule: Daily at 3:00 AM
CRON_SCHEDULE="0 3 * * *"

# Full cron entry
CRON_ENTRY="$CRON_SCHEDULE $PIPELINE_CMD >> $LOG_FILE 2>&1"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

install_cron() {
    echo -e "${GREEN}Installing PokeWatch pipeline cron job...${NC}"
    echo ""

    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "pipelines.ml_pipeline"; then
        echo -e "${YELLOW}⚠ Cron job already exists!${NC}"
        echo "Run './scripts/schedule_pipeline.sh remove' first to update"
        exit 1
    fi

    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

    echo -e "${GREEN}✓ Cron job installed successfully!${NC}"
    echo ""
    echo "Schedule: $CRON_SCHEDULE (Daily at 3:00 AM)"
    echo "Command:  $PIPELINE_CMD"
    echo "Logs:     $LOG_FILE"
    echo ""
    echo "To verify: crontab -l"
}

remove_cron() {
    echo -e "${YELLOW}Removing PokeWatch pipeline cron job...${NC}"
    echo ""

    # Check if cron job exists
    if ! crontab -l 2>/dev/null | grep -q "pipelines.ml_pipeline"; then
        echo -e "${RED}✗ No cron job found${NC}"
        exit 1
    fi

    # Remove cron job
    crontab -l 2>/dev/null | grep -v "pipelines.ml_pipeline" | crontab -

    echo -e "${GREEN}✓ Cron job removed${NC}"
}

status_cron() {
    echo "PokeWatch Pipeline Schedule Status"
    echo "===================================="
    echo ""

    if crontab -l 2>/dev/null | grep -q "pipelines.ml_pipeline"; then
        echo -e "${GREEN}✓ Scheduled${NC}"
        echo ""
        echo "Cron entry:"
        crontab -l 2>/dev/null | grep "pipelines.ml_pipeline"
        echo ""
        echo "Schedule: $CRON_SCHEDULE (Daily at 3:00 AM)"
        echo "Log file: $LOG_FILE"

        # Show last 10 lines of log if it exists
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Last 10 log entries:"
            echo "--------------------"
            tail -n 10 "$LOG_FILE"
        fi
    else
        echo -e "${RED}✗ Not scheduled${NC}"
        echo ""
        echo "Run './scripts/schedule_pipeline.sh install' to schedule"
    fi
}

# Main command handler
case "${1:-}" in
    install)
        install_cron
        ;;
    remove)
        remove_cron
        ;;
    status)
        status_cron
        ;;
    *)
        echo "Usage: $0 {install|remove|status}"
        echo ""
        echo "Commands:"
        echo "  install  - Add pipeline to cron (daily at 3:00 AM)"
        echo "  remove   - Remove pipeline from cron"
        echo "  status   - Check scheduling status"
        echo ""
        echo "Examples:"
        echo "  $0 install   # Schedule the pipeline"
        echo "  $0 status    # Check if scheduled"
        echo "  $0 remove    # Unschedule the pipeline"
        exit 1
        ;;
esac
