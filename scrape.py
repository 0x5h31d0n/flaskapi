import cloudscraper
import time
import json
from bs4 import BeautifulSoup
from datetime import datetime
import random
import os

class MLHScraper:
    def __init__(self):
        self.mlh_url = "https://mlh.io/seasons/2025/events"
        self.hackerearth_url = "https://www.hackerearth.com/challenges/hackathon/"
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        self.cache_file = os.path.join(self.cache_dir, 'hackathons_cache.json')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )

    def should_update_cache(self):
        if not os.path.exists(self.cache_file):
            return True
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                last_update = datetime.fromtimestamp(cache_data['timestamp'])
                return last_update.date() < datetime.now().date()
        except:
            return True

    def load_cached_data(self):
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data['data']
        except:
            return None

    def save_to_cache(self, data):
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

    def fetch_page(self, url):
        try:
            time.sleep(random.uniform(2, 5))
            response = self.scraper.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching page {url}: {e}")
            return None

    def parse_mlh_hackathon(self, event_div):
        try:
            hackathon = self.parse_hackathon(event_div)
            if hackathon:
                hackathon['source'] = 'MLH'
            return hackathon
        except Exception as e:
            print(f"Error parsing MLH hackathon: {e}")
            return None

    def parse_hackerearth_hackathon(self, event_div):
        try:
            # Parse HackerEarth specific structure
            name = event_div.find("div", class_="challenge-name").text.strip()
            date_div = event_div.find("div", class_="date")
            date_text = date_div.text.strip() if date_div else "Date TBA"
            
            # Get location (HackerEarth hackathons are usually online)
            location = "Online, Worldwide"
            
            # Get event URL
            event_link = event_div.find("a", class_="challenge-card-wrapper")
            url = event_link['href'] if event_link else ""
            if url and not url.startswith('http'):
                url = f"https://www.hackerearth.com{url}"
            
            # Get images
            image_div = event_div.find("div", class_="event-image")
            background_image = image_div['style'].split('url(\'')[1].split('\')')[0] if image_div else None
            
            return {
                "name": name,
                "date": date_text,
                "location": location,
                "event_type": "Digital Only",
                "background_image": background_image,
                "logo_image": None,
                "event_url": url,
                "is_diversity_event": False,
                "diversity_type": "",
                "source": "HackerEarth"
            }
        except Exception as e:
            print(f"Error parsing HackerEarth hackathon: {e}")
            return None

    def scrape_hackathons(self):
        # Check if we need to update cache
        if not self.should_update_cache():
            cached_data = self.load_cached_data()
            if cached_data:
                return cached_data

        # If cache is outdated or doesn't exist, scrape new data
        hackathons = []
        
        # Scrape MLH events
        mlh_content = self.fetch_page(self.mlh_url)
        if mlh_content:
            soup = BeautifulSoup(mlh_content, 'html.parser')
            past_events_header = soup.find('h3', class_='text-center mb-3', string='Past Events')
            
            current_events = []
            for event in soup.find_all("div", class_="event-wrapper"):
                if past_events_header and past_events_header in event.find_previous_siblings():
                    break
                current_events.append(event)
            
            for event_div in current_events:
                hackathon = self.parse_mlh_hackathon(event_div)
                if hackathon:
                    hackathons.append(hackathon)
        
        # Scrape HackerEarth events
        he_content = self.fetch_page(self.hackerearth_url)
        if he_content:
            soup = BeautifulSoup(he_content, 'html.parser')
            he_events = soup.find_all("div", class_="challenge-card-modern")
            
            for event_div in he_events:
                hackathon = self.parse_hackerearth_hackathon(event_div)
                if hackathon:
                    hackathons.append(hackathon)
        
        # Save to cache before returning
        self.save_to_cache(hackathons)
        return hackathons

    def parse_hackathon(self, event_div):
        try:
            # Extract basic information
            name = event_div.find("h3", class_="event-name").text.strip()
            
            # Extract date
            date_text = event_div.find("p", class_="event-date").text.strip()
            
            # Extract location
            location_div = event_div.find("div", class_="event-location")
            city = location_div.find("span", itemprop="city").text.strip()
            state = location_div.find("span", itemprop="state").text.strip()
            location = f"{city}, {state}"
            
            # Extract event type
            event_type = event_div.find("div", class_="event-hybrid-notes").text.strip()
            
            # Extract images
            image_wrap = event_div.find("div", class_="image-wrap")
            background_image = image_wrap.find("img")["src"] if image_wrap else None
            
            logo_div = event_div.find("div", class_="event-logo")
            logo_image = logo_div.find("img")["src"] if logo_div else None
            
            # Extract event URL
            event_link = event_div.find("a", class_="event-link")["href"]
            
            # Check if it's a diversity event
            is_diversity = bool(event_div.find("span", class_="diversity-event-badge"))
            diversity_type = ""
            if is_diversity:
                diversity_badge = event_div.find("span", class_="diversity-event-badge")
                diversity_type = diversity_badge["title"] if diversity_badge else ""

            return {
                "name": name,
                "date": date_text,
                "location": location,
                "event_type": event_type,
                "background_image": background_image,
                "logo_image": logo_image,
                "event_url": event_link,
                "is_diversity_event": is_diversity,
                "diversity_type": diversity_type
            }
        except Exception as e:
            print(f"Error parsing hackathon: {e}")
            return None

    def save_to_json(self, hackathons, filename="hackathons.json"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(hackathons, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")

def main():
    scraper = MLHScraper()
    hackathons = scraper.scrape_hackathons()
    
    # Create a timestamp for the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hackathons_{timestamp}.json"
    
    scraper.save_to_json(hackathons, filename)
    
    # Print summary
    print(f"\nScraped {len(hackathons)} hackathons")
    print("\nSample hackathon details:")
    if hackathons:
        print(json.dumps(hackathons[0], indent=2))

if __name__ == "__main__":
    main()