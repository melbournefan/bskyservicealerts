import requests
from google.transit import gtfs_realtime_pb2
from atproto import Client, models
import datetime
import schedule
from keys import BSKYUSERNAME, BSKYPASSWORD, GTFSRKEY
import time

gtfsurl = "https://data-exchange-api.vicroads.vic.gov.au/opendata/gtfsr/v1/tram/servicealert"
headerbase = {'cache-control' : 'no-cache'}
headerkey = {'Ocp-Apim-Subscription-Key' : GTFSRKEY}



postedalerts = set

def checkpostedalerts():
    global postedalerts
    response  = requests.get(gtfsurl, headers=headerbase+headerkey)

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    old_alerts = set()
    new_alerts = []

    for entity in feed.entity:
        if entity.HasField("alert"):
            alert = entity.alert
            title = alert.header_text.translation[0].text if alert.header_text.translation else ""
            description = alert.description_text.translation[0].text if alert.description_text.translation else ""
            alert_text = f"{description}"
            new_alerts.add(alert_text)

    new_alerts = new_alerts - old_alerts

    if new_alerts:
        post_text = "\n\n".join(new_alerts)
        
        bskyclient =()
        bskyclient.login(BSKYUSERNAME, BSKYPASSWORD)

        final_post = models.AppBsky.FeedPost.Record(
            text=post_text,
            created_at=datetime.datetime.now().isoformat().replace('+00:00', 'Z')
        )

        bsky_response = Client.com.atprotocol.repo.create_record(
            repo=Client.me.did,
            collection=models.ids.AppBskyFeedPost,
            record=final_post
        )
        print(f"Alert pushed to Bluesky : {bsky_response.uri}")

    old_alerts.update(new_alerts)
    

    schedule.every(3).minutes.do(checkpostedalerts)
    while True:
        schedule.run_pending()
        time.sleep(1)
