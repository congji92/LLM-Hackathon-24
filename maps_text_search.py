import pandas as pd # pip install pandas
from google_apis import create_service

client_secret_file = 'client-secret.json'
API_NAME = 'places'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
import requests
API_KEY = 'Google Maps API Here'

class Agent_search(object):
    def __init__(
            self, 
            destination,
            query,
    ):
        self.destination = destination
        self.query = query
        self.client_secret_file = 'client-secret.json'
        self.API_NAME = 'places'
        self.API_VERSION = 'v1'
        self.SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
        self.service = create_service(client_secret_file, API_NAME, API_VERSION, SCOPES)
        
        self.params = {
            'key': API_KEY,
            'address': self.destination.replace(' ', '+')
        }
        self.base_url = 'https://maps.googleapis.com/maps/api/geocode/json?'
        self.response = requests.get(self.base_url, params= self.params)
        self.data = self.response.json()
        if self.data['status'] == 'OK':
            location = self.data['results'][0]['geometry']['viewport']
            self.lLat = location['southwest']['lat']
            self.lLong = location['southwest']['lng']
            self.hLat = location['northeast']['lat']
            self.hLong = location['northeast']['lng']
            print('debug llat: ', self.lLat)
            print('debug llng: ',self.lLong)
            print('debug hlat: ',self.hLat)
            print('debug hlng: ',self.hLong)
        
        self.request_body = {
            'textQuery': self.query,
            'regionCode': 'US',
            'locationRestriction':{
                'rectangle': {
                    'high': {
                        "latitude": self.hLat, "longitude": self.hLong
                    },
                    'low': {
                        "latitude": self.lLat, "longitude": self.lLong
                    }
                }           
            },
            'priceLevels': ['PRICE_LEVEL_MODERATE']
        }
    
    def search(self):
        response = self.service.places().searchText(
        body = self.request_body,
        fields = '*'
        ).execute()

        places_list = response['places']
        df = pd.json_normalize(places_list)['displayName.text']
        df.to_csv('places_results_agent.csv', index = False)
        return df
