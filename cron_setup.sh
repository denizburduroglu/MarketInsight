#!/bin/bash

# S&P 500 Metrics Worker CRON Setup Script
# This script sets up a CRON job to run the S&P 500 worker every minute

# Configuration
PROJECT_DIR="/path/to/your/MarketInsight"  # Update this path
PYTHON_ENV="/path/to/your/venv/bin/python"  # Update this path to your virtual environment
LOG_DIR="$PROJECT_DIR/logs"
WORKER_LOG="$LOG_DIR/sp500_worker.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create the cron job script
CRON_SCRIPT="$PROJECT_DIR/run_sp500_worker.sh"

cat > "$CRON_SCRIPT" << 'EOF'
#!/bin/bash

# Set the path to your project and virtual environment
PROJECT_DIR="/path/to/your/MarketInsight"  # Update this path
PYTHON_ENV="/path/to/your/venv/bin/python"  # Update this path
LOG_FILE="$PROJECT_DIR/logs/sp500_worker.log"

# Change to project directory
cd "$PROJECT_DIR"

# Run the worker with limited batch size to respect rate limits
# Process 10 companies per run with 1 second delay between requests
$PYTHON_ENV manage.py sp500_worker --batch-size=10 --delay=1.0 --max-companies=10 >> "$LOG_FILE" 2>&1

# Optional: Clean up old log entries (keep last 1000 lines)
tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
EOF

# Make the script executable
chmod +x "$CRON_SCRIPT"

# Create the cron job entry
CRON_JOB="* * * * * $CRON_SCRIPT"

# Add the cron job (check if it already exists first)
(crontab -l 2>/dev/null | grep -v "$CRON_SCRIPT"; echo "$CRON_JOB") | crontab -

echo "CRON job has been set up successfully!"
echo "The worker will run every minute and process 10 companies per run."
echo "Logs will be written to: $WORKER_LOG"
echo ""
echo "To monitor the worker:"
echo "  tail -f $WORKER_LOG"
echo ""
echo "To disable the cron job:"
echo "  crontab -e"
echo "  # Then remove or comment out the line containing: $CRON_SCRIPT"
echo ""
echo "IMPORTANT: Update the paths in $CRON_SCRIPT before using!"