import pandas as pd # pip install pandas
from google_apis import create_service

client_secret_file = 'client-secret.json'
API_NAME = 'places'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

class Agent_search(object):
    def __init__(
            self, 
            query,
            hLat,
            hLong,
            lLat,
            lLong,
    ):
        self.query = query
        self.hLat = 37.802516
        self.hLong = -122.399833
        self.lLat = 37.775271
        self.lLong = -122.431116
        self.client_secret_file = 'client-secret.json'
        self.API_NAME = 'places'
        self.API_VERSION = 'v1'
        self.SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
        self.service = create_service(client_secret_file, API_NAME, API_VERSION, SCOPES)
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
        df.to_csv('places_results.csv', index = False)
        return df