# S&P 500 Metrics Worker System

This system provides automated fetching of S&P 500 company metrics from the Finnhub API using a worker-based approach with proper rate limiting.

## Features

- **Automated Data Fetching**: Fetches real-time stock data, financials, and company profiles
- **Rate Limiting**: Respects Finnhub API limits (60 calls per minute for free tier)
- **Batch Processing**: Processes companies in configurable batches
- **Enhanced Metrics**: Includes daily, monthly, and yearly price changes
- **Sector Information**: Fetches and stores company sector data
- **Windows Compatible**: Includes both Linux/Unix CRON and Windows Task Scheduler support

## New Model Fields Added

The `CompanyMetrics` model now includes:

- `daily_change` - Daily price change in dollars
- `daily_change_percent` - Daily price change percentage
- `monthly_change` - Monthly price change in dollars
- `monthly_change_percent` - Monthly price change percentage
- `yearly_change` - Yearly price change in dollars
- `yearly_change_percent` - Yearly price change percentage
- `sector` - Company sector information

## Usage

### Manual Execution

```bash
# Run worker for all companies that need updates
python manage.py sp500_worker

# Run with custom parameters
python manage.py sp500_worker --batch-size=10 --delay=1.0 --max-companies=50

# Force update all companies (ignore if already updated today)
python manage.py sp500_worker --force

# Process specific number of companies
python manage.py sp500_worker --max-companies=20
```

### Parameters

- `--batch-size`: Number of companies to process per batch (default: 10)
- `--delay`: Delay between API calls in seconds (default: 1.0)
- `--max-companies`: Maximum number of companies to process in this run
- `--force`: Force update even if data already exists for today

## Automation Setup

### Linux/Unix (CRON)

1. Make the setup script executable:
   ```bash
   chmod +x cron_setup.sh
   ```

2. Edit the script to update paths:
   ```bash
   nano cron_setup.sh
   # Update PROJECT_DIR and PYTHON_ENV variables
   ```

3. Run the setup:
   ```bash
   ./cron_setup.sh
   ```

### Windows (Task Scheduler)

1. Edit the batch file paths:
   ```batch
   # Edit run_sp500_worker.bat
   # Update PROJECT_DIR and PYTHON_EXE variables
   ```

2. Run PowerShell as Administrator and execute:
   ```powershell
   .\setup_windows_scheduler.ps1
   ```

## Rate Limiting Strategy

The worker is designed to respect Finnhub's rate limits:

- **Free Tier**: 60 calls per minute
- **Worker Strategy**: Process 10 companies per minute with 1-second delays
- **Daily Coverage**: With 500 S&P companies, full update takes ~50 minutes
- **Continuous Operation**: Runs every minute, processing only companies that need updates

## Monitoring

### Log Files

- **Linux**: Check `/path/to/project/logs/sp500_worker.log`
- **Windows**: Check `C:\path\to\project\logs\sp500_worker.log`

### Log Monitoring Commands

```bash
# Watch real-time logs
tail -f logs/sp500_worker.log

# View recent entries
tail -n 50 logs/sp500_worker.log

# Search for errors
grep "ERROR\|FAILED" logs/sp500_worker.log
```

## Database Migration

After adding new fields, run:

```bash
python manage.py makemigrations insights
python manage.py migrate
```

## API Configuration

Ensure your `.env` file has a valid Finnhub API key:

```env
FINNHUB_API_KEY=your_actual_api_key_here
```

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Verify `FINNHUB_API_KEY` is set correctly
   - Check if you've exceeded your API limits

2. **Rate Limiting**
   - Increase `--delay` parameter
   - Reduce `--batch-size` parameter

3. **Windows Unicode Issues**
   - The worker uses ASCII-compatible symbols for Windows compatibility

4. **Database Errors**
   - Ensure migrations are applied
   - Check database connectivity

### Performance Tuning

- **For Premium API**: Increase batch size and reduce delay
- **For Free API**: Keep default settings (10 companies per minute)
- **For Testing**: Use `--max-companies` to limit scope

## System Architecture

1. **Worker Command**: `sp500_worker.py` - Main worker logic
2. **Scheduler**: CRON (Linux) or Task Scheduler (Windows)
3. **Rate Limiting**: Built-in delays and batch processing
4. **Data Storage**: Django ORM with CompanyMetrics model
5. **Logging**: Comprehensive logging to files

The system is designed to run continuously, ensuring your S&P 500 data stays current throughout market hours.