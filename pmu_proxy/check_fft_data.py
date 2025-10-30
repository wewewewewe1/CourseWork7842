# Quick check if FFT data exists in database
from influxdb import InfluxDBClient

HOST, PORT = "127.0.0.1", 8086
ANALYSIS_DB = "pmu_analysis"

client = InfluxDBClient(host=HOST, port=PORT, database=ANALYSIS_DB)

print("=" * 60)
print("Checking FFT data in pmu_analysis database")
print("=" * 60)

# Check if database exists
try:
    databases = client.get_list_database()
    db_names = [db['name'] for db in databases]
    print(f"\nAvailable databases: {db_names}")

    if ANALYSIS_DB not in db_names:
        print(f"\n[ERROR] Database '{ANALYSIS_DB}' does not exist!")
        print("The api_server.py should create it automatically when started.")
        exit(1)

    print(f"\n[OK] Database '{ANALYSIS_DB}' exists")

    # Check measurements
    measurements = client.get_list_measurements()
    meas_names = [m['name'] for m in measurements]
    print(f"\nMeasurements in {ANALYSIS_DB}: {meas_names}")

    # Check FFT data
    q_summary = 'SELECT COUNT(*) FROM "fft_summary"'
    q_spectrum = 'SELECT COUNT(*) FROM "fft_spectrum"'

    summary_count = list(client.query(q_summary).get_points())[0]['count_dominant_freq']
    spectrum_count = list(client.query(q_spectrum).get_points())[0]['count_magnitude']

    print(f"\nFFT summary records: {summary_count}")
    print(f"FFT spectrum records: {spectrum_count}")

    if summary_count == 0:
        print("\n[WARNING] No FFT data found!")
        print("Possible causes:")
        print("  1. api_server.py is not running")
        print("  2. fake_writer.py is not generating data")
        print("  3. AnalysisManager is not running properly")
    else:
        print(f"\n[OK] FFT data exists")

        # Show latest FFT result
        q_latest = 'SELECT * FROM "fft_summary" ORDER BY time DESC LIMIT 1'
        latest = list(client.query(q_latest).get_points())[0]
        print(f"\nLatest FFT result:")
        print(f"  Signal: {latest.get('signal_id')}")
        print(f"  Dominant Freq: {latest.get('dominant_freq')} Hz")
        print(f"  Time: {latest.get('time')}")

except Exception as e:
    print(f"\n[ERROR] {e}")

print("=" * 60)
