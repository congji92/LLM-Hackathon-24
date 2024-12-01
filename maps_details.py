#import pandas as pd # pip install pandas
from google_apis import create_service

client_secret_file = 'client-secret.json'
API_NAME = 'places'
API_VERSION = 'v1'
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

service = create_service(client_secret_file, API_NAME, API_VERSION, SCOPES)

response = service.places().get(
    name='places/ChIJ-_KJwyZawokRkV_qFDf6IxI',
    fields='*'
).execute()

# response.keys()
#df = pd.json_normalize(response)
#df.to_csv('places_details.csv', index=False)