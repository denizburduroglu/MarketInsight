import time
from datetime import datetime, time as dt_time
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Run daily S&P 500 data collection at market close (4:30 PM ET)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-once',
            action='store_true',
            help='Run collection once and exit (for testing)',
        )
        parser.add_argument(
            '--target-time',
            type=str,
            default='16:30',
            help='Target time to run collection (HH:MM format, default: 16:30)',
        )

    def handle(self, *args, **options):
        run_once = options['run_once']
        target_time_str = options['target_time']

        try:
            target_hour, target_minute = map(int, target_time_str.split(':'))
            target_time = dt_time(target_hour, target_minute)
        except ValueError:
            self.stdout.write(
                self.style.ERROR(
                    'Invalid time format. Use HH:MM format (e.g., 16:30)'
                )
            )
            return

        self.stdout.write(
            f'Daily S&P 500 collection scheduler started. '
            f'Target time: {target_time_str}'
        )

        if run_once:
            self.stdout.write('Running collection once...')
            self.run_collection()
            return

        collection_run_today = False
        last_check_date = datetime.now().date()

        while True:
            try:
                now = datetime.now()
                current_time = now.time()
                current_date = now.date()

                # Reset the flag if it's a new day
                if current_date != last_check_date:
                    collection_run_today = False
                    last_check_date = current_date
                    self.stdout.write(f'New day detected: {current_date}')

                # Check if it's time to run and we haven't run today
                if (current_time >= target_time and
                    not collection_run_today and
                    current_date.weekday() < 5):  # Monday = 0, Friday = 4 (weekdays only)

                    self.stdout.write(
                        f'Starting S&P 500 data collection at {now.strftime("%H:%M:%S")}'
                    )
                    self.run_collection()
                    collection_run_today = True
                    self.stdout.write('Collection completed. Waiting for next day...')

                # Sleep for 60 seconds before checking again
                time.sleep(60)

            except KeyboardInterrupt:
                self.stdout.write('\nScheduler stopped by user')
                break
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error in scheduler: {str(e)}')
                )
                time.sleep(60)  # Wait a minute before retrying

    def run_collection(self):
        """Run the data collection process"""
        try:
            # First populate S&P 500 companies if needed
            self.stdout.write('Ensuring S&P 500 companies are populated...')
            call_command('populate_sp500')

            # Then collect the daily data
            self.stdout.write('Starting data collection...')
            call_command('collect_sp500_data')

            self.stdout.write(
                self.style.SUCCESS(
                    'Daily collection completed successfully!'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error during collection: {str(e)}'
                )
            )