from flask import Flask, jsonify
from scrape import MLHScraper
import time
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
import atexit

app = Flask(__name__)
scraper = MLHScraper()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache to store results and reduce API calls
cache = {
    'data': None,
    'last_update': 0,
    'cache_duration': 86400  # Cache for 24 hours (once a day)
}

def refresh_cache():
    """Force a cache refresh, regardless of when it was last updated"""
    logger.info(f"Scheduled cache refresh started at {datetime.now()}")
    try:
        cache['data'] = scraper.scrape_hackathons()
        cache['last_update'] = time.time()
        logger.info(f"Cache successfully refreshed. Found {len(cache['data'])} hackathons")
    except Exception as e:
        logger.error(f"Error refreshing cache: {str(e)}")

def get_cached_data():
    current_time = time.time()
    if not cache['data'] or (current_time - cache['last_update']) > cache['cache_duration']:
        logger.info("Cache expired or empty, fetching fresh data")
        refresh_cache()
    return cache['data']

# Set up the scheduler to refresh cache daily at 2:00 AM
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_cache, trigger="cron", hour=2, minute=0)
scheduler.start()

# Register the shutdown function
atexit.register(lambda: scheduler.shutdown(wait=False))

@app.route('/api/hackathons', methods=['GET'])
def get_hackathons():
    try:
        hackathons = get_cached_data()
        return jsonify({
            'status': 'success',
            'count': len(hackathons),
            'data': hackathons
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/hackathons/<source>', methods=['GET'])
def get_hackathons_by_source(source):
    try:
        hackathons = get_cached_data()
        filtered_hackathons = [h for h in hackathons if h['source'].lower() == source.lower()]
        return jsonify({
            'status': 'success',
            'count': len(filtered_hackathons),
            'data': filtered_hackathons
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/clear-cache', methods=['GET'])
def clear_cache():
    cache['data'] = None
    cache['last_update'] = 0
    return jsonify({
        'status': 'success',
        'message': 'Cache cleared successfully'
    })

@app.route('/api/connectivity-check', methods=['GET'])
def connectivity_check():
    results = {}
    urls = [
        "https://www.google.com",
        "https://www.hackerearth.com",
        "https://mlh.io"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            results[url] = {
                "status": "success",
                "status_code": response.status_code,
                "content_length": len(response.content)
            }
        except Exception as e:
            results[url] = {
                "status": "error",
                "message": str(e)
            }
    
    return jsonify({
        "status": "success",
        "results": results
    })

@app.route('/api/cache-status', methods=['GET'])
def cache_status():
    current_time = time.time()
    last_update = cache['last_update']
    time_since_update = current_time - last_update if last_update > 0 else 0
    
    next_scheduled_refresh = None
    for job in scheduler.get_jobs():
        next_scheduled_refresh = job.next_run_time
        break
    
    return jsonify({
        'status': 'success',
        'cache_populated': cache['data'] is not None,
        'hackathon_count': len(cache['data']) if cache['data'] else 0,
        'last_update': last_update,
        'last_update_readable': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_update)) if last_update > 0 else 'Never',
        'time_since_update_hours': round(time_since_update / 3600, 2),
        'next_scheduled_refresh': next_scheduled_refresh.strftime('%Y-%m-%d %H:%M:%S') if next_scheduled_refresh else 'Not scheduled',
        'cache_duration_hours': cache['cache_duration'] / 3600
    })

if __name__ == '__main__':
    # On startup, make sure we have data
    if not cache['data']:
        refresh_cache()
    
    app.run(debug=True, port=5000)