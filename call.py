import requests
from google.transit import gtfs_realtime_pb2
from atproto import Client, models
import datetime
import schedule
from keys import BSKYUSERNAME, BSKYPASSWORD, GTFSRKEY
import time
import sqlite3

gtfsurl = "https://data-exchange-api.vicroads.vic.gov.au/opendata/gtfsr/v1/tram/servicealert"
header = {'cache-control' : 'no-cache', 'Ocp-Apim-Subscription-Key' : GTFSRKEY }
DBFILE = "servicealerts.db"
BSKYPASSWORD = BSKYPASSWORD
BSKYUSERNAME = BSKYUSERNAME
GTFSRKEY = GTFSRKEY


postedalerts = set

def checkexistingalert(alert_text):
    try:
        conn = sqlite3.connect(DBFILE)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM alerts WHERE alert_text = ?", (alert_text,))
        exists = cursor.fetchone() is not None
        conn.close()
        return(checkexistingalert)
    except sqlite3.Error as  chker:
        print(f"Error checking DB",{chker})
        return False

def insert_alert_into_db(alert_text, title, description):
    """
    Inserts a new alert into the database.

    Args:
        alert_text (str): The text of the alert.
        title (str): The title of the alert.
        description (str): The description of the alert.

    Returns:
        bool: True on success, False on failure.
    """
    try:
        conn = sqlite3.connect(DBFILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alerts (alert_text, title, description, created_at) VALUES (?, ?, ?, ?)",
            (alert_text, title, description, datetime.datetime.now().isoformat())  # Corrected execute syntax
        )
        conn.commit()
        conn.close()
        print(f"Inserted Alert into DB at {datetime.datetime.now().isoformat()}")
        return True # Explicitly return True on success
    except sqlite3.Error as e:
        print(f"Error inserting into DB: {e}")
        return False


def post_alert_then_add():
    """
    Fetches the latest alert, posts it to Bluesky, and adds it to the database.
    """
    try:
        response = requests.get(gtfsurl, headers=header)
        response.raise_for_status()  # Raise HTTPError for bad responses (better error handling)
        livefeed = gtfs_realtime_pb2.FeedMessage()
        livefeed.ParseFromString(response.content)

        if livefeed.entity:
            for entity in livefeed.entity:
                if entity.HasField("alert"):
                    alert = entity.alert
                    title = alert.header_text.translation[0].text if alert.header_text.translation else ""
                    description = alert.description_text.translation[0].text if alert.description_text.translation else ""
                    final_text = f"{description}" # Removed redundant f-string

                    if not checkexistingalert(final_text):
                        # then post to BSky
                        bskyclient = Client()
                        try:
                            bskyclient.login(BSKYUSERNAME, BSKYPASSWORD)
                            final_post = models.AppBsky.FeedPost.Record(
                                text=final_text,
                                created_at=datetime.datetime.now().isoformat()
                            )
                            bsky_response = bskyclient.com.atproto.repo.create_record(
                                repo=bskyclient.me.did,
                                collection=models.ids.AppBskyFeedPost,
                                record=final_post
                            )
                            print(f"Alert pushed to Bluesky: {bsky_response.uri}")
                            postedalerts.add(final_text)

                            # then insert into DB
                            if insert_alert_into_db(final_text, title, description):
                                print("Alert pushed into DB")
                            else:
                                print("Failed to push alert into DB")
                        except Exception as bsky_exc:
                            print(f"Error posting to Bluesky: {bsky_exc}")
                    else:
                        print("Alert already exists in DB")
        else: #Added else
            print("No alerts found in GTFS feed.") #Added message
    except requests.exceptions.RequestException as req_exc:
        print(f"Error fetching GTFS feed: {req_exc}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def check_for_new_alerts():
    """
    Checks for new alerts in the GTFS feed compared to the database and prints them.
    """
    try:
        response = requests.get(gtfsurl, headers=header)
        response.raise_for_status()
        livefeed = gtfs_realtime_pb2.FeedMessage()
        livefeed.ParseFromString(response.content)

        db_alerts = checkexistingalert()  # Get alerts from the database
        new_alerts = []

        if livefeed.entity:
            for entity in livefeed.entity:
                if entity.HasField("alert"):
                    alert = entity.alert
                    description = (
                        alert.description_text.translation[0].text
                        if alert.description_text.translation
                        else ""
                    )
                    final_text = f"{description}"

                    if final_text not in db_alerts:
                        new_alerts.append(final_text)

        if new_alerts:
            print("New alerts found:")
            for alert_text in new_alerts:
                print(f"- {alert_text}")  # Print each new alert
        else:
            print("No new alerts.")

    except requests.exceptions.RequestException as req_exc:
        print(f"Error fetching GTFS feed: {req_exc}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


        if __name__ == "__main__":
            check_for_new_alerts()

schedule.every(3).minutes.do(check_for_new_alerts)
while True:
    schedule.run_pending()
    time.sleep(1)
