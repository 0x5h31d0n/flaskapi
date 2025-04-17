from flask import Flask, jsonify
from scrape import MLHScraper
import time

app = Flask(__name__)
scraper = MLHScraper()

# Cache to store results and reduce API calls
cache = {
    'data': None,
    'last_update': 0,
    'cache_duration': 3600  # Cache for 1 hour
}

def get_cached_data():
    current_time = time.time()
    if not cache['data'] or (current_time - cache['last_update']) > cache['cache_duration']:
        cache['data'] = scraper.scrape_hackathons()
        cache['last_update'] = current_time
    return cache['data']

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)