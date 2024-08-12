from flask import Flask, request
import requests
import os
import json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from datetime import datetime, timezone

app = Flask(__name__)

CORTEX_URL = "https://cortex-staging.prosimo.us/metrics/job/opsgenie_alerts/instance/%s"
ES_HOST = os.environ.get('ES_HOST')
ES_PORT = os.environ.get('ES_PORT')

es = Elasticsearch(
    hosts=[{'host': ES_HOST, 'port': int(ES_PORT), 'scheme': 'http'}],
    verify_certs=False
)

def get_alerts_count():
    search_body = {
        "query": {
            "match_all": {}
        }
    }
    response = es.count(index="alerts", body=search_body)
    return response['count']

def get_open_alerts_count():
    search_body = {
        "query": {
            "term": {
                "closeStatus": "open"
            }
        }
    }
    response = es.count(index="alerts", body=search_body)
    return response['count']

def get_closed_alerts_count():
    search_body = {
        "query": {
            "term": {
                "closeStatus": "closed"
            }
        }
    }
    response = es.count(index="alerts", body=search_body)
    return response['count']

def update_alerts_count():
    alerts_count = get_alerts_count()
    open_alerts_count = get_open_alerts_count()
    closed_alerts_count = get_closed_alerts_count()
    timestamp = datetime.now(timezone.utc).isoformat()

    doc = {
        "timestamp": timestamp,
        "alerts_count": alerts_count,
        "open_alerts_count": open_alerts_count,
        "closed_alerts_count": closed_alerts_count
    }

    es.index(index="alerts-count", document=doc)
    print(f"Alerts count updated: {alerts_count} at {timestamp}, open: {open_alerts_count}, closed: {closed_alerts_count}")

def calculate_time_to_resolve(created_at, closed_at):
    created_at_datetime = datetime.fromtimestamp(created_at / 1000.0, tz=timezone.utc)
    closed_at_datetime = datetime.fromtimestamp(closed_at / 1000000000.0, tz=timezone.utc)
    time_to_resolve = closed_at_datetime - created_at_datetime
    return time_to_resolve.total_seconds() / 60

def generate_prometheus_metric(alert):
    tags = alert.get('alert').get('tags')
    alert_name = alert.get('alert').get('details').get('alertname', '')
    priority = alert.get('alert').get('priority')
    alert_state = 'closed' if alert.get('action') == 'Close' else 'firing'
    details = alert.get('alert').get('details')
    details_string = ""
    if len(details) != 0:
        details_string = ", "
        for key, value in details.items():
            if key == "alertname":
                continue
            details_string += f'{key}="{value}", '
        details_string = details_string[:-2]
    metric_data = ('# TYPE opsgenie_alerts gauge\n opsgenie_alerts{alertname="%s", priority="%s", tags="%s", alertstate="%s"%s} 1.0\n' % (alert_name, priority, tags, alert_state, details_string))
    return metric_data

@app.route('/', methods=['POST'])
def publish_message():
    received_auth_token = request.headers.get('Authorization')
    if received_auth_token != os.environ.get('OPSGENIE_AUTH'):
        return {
            'statusCode': 401,
            'body': json.dumps('Unauthorized')
        }

    data = request.data
    try:
        alert = json.loads(data)
        print(f'Received alert: {alert}')
        metric_data = generate_prometheus_metric(alert)
        headers = {
            "X-Requested-With": "Python requests",
            "Content-type": "text/plain",
        }
        cortex_instance_url = CORTEX_URL % alert.get('alert').get('details').get('alertname', 'unknown')
        response = requests.post(
            cortex_instance_url,
            headers=headers,
            data=metric_data,
            cert=(
                "nginx.crt",
                "nginx.key",
            ),
            verify="rootCA.crt"
        )
        print(f"Opsgenie to Cortex URL {cortex_instance_url}: " + response.reason + ", Metric: " + metric_data)
    except Exception as err:
        print(f"Exception seen during alert post to Cortex - {err}")

    try:
        message = json.loads(data)
        alert_id = message.get('alert').get('alertId')
        action = message.get('action')
        alert_url = f'https://prosimoio.app.opsgenie.com/alert/detail/{alert_id}/details'

        if action == 'Create':
            created_at = message.get('alert').get('createdAt')
            minute_updated = datetime.fromtimestamp(int(created_at) / 1000.0, tz=timezone.utc).isoformat()
            default_fields = {
                'closeStatus': "open",
                'closeTimestamp': None,
                'alertURL': alert_url,
                'minuteUpdated': minute_updated
            }
            message.update(default_fields)
            es.index(index="alerts", id=alert_id, document=message)
            print(f'Alert {alert_id} created and indexed in Elasticsearch')
            minute_updated_for_actions = datetime.fromtimestamp(int(created_at) / 1000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:00')
            new_entry_id = (es.count(index="alerts-actions"))['count']
            es.index(index="alerts-actions", id = new_entry_id, document= {"id": new_entry_id, "minuteUpdated": minute_updated_for_actions, "actionType": "open"})
            update_alerts_count()
        elif action == 'Close':
            try:
                close_timestamp = message.get('alert').get('updatedAt')
                created_at = message.get('alert').get('createdAt')
                created_at = int(created_at)
                close_timestamp = int(close_timestamp)
                time_to_resolve_mins = calculate_time_to_resolve(created_at, close_timestamp)
                minute_updated = datetime.fromtimestamp(close_timestamp / 1000000000.0, tz=timezone.utc).isoformat()
                update_body = {
                    "doc": {
                        "closeStatus": 'closed',
                        "closeTimestamp": close_timestamp,
                        "timeToResolve": time_to_resolve_mins,
                        'minuteUpdated': minute_updated
                    }
                }
                es.update(index="alerts", id=alert_id, body=update_body)
                print(f'Alert {alert_id} updated in Elasticsearch with close fields')
                new_entry_id = es.count(index="alerts-actions")['count']
                minute_updated_for_actions = datetime.fromtimestamp(close_timestamp / 1000000000.0, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:00')
                es.index(index="alerts-actions", id = new_entry_id, document= {"id": new_entry_id, "minuteUpdated": minute_updated_for_actions, "actionType": "close"})
                update_alerts_count()
            except NotFoundError:
                print(f'Alert {alert_id} not found in Elasticsearch for close action')

        return {
            'statusCode': 200,
            'body': json.dumps('alert processed for elasticsearch')
        }
    except Exception as err:
        print(f"Exception seen during alert processing for elasticsearch - {err}")
        return {
            'statusCode': 400,
            'body': json.dumps('alert processing for elasticsearch failed')
        }

if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(host='0.0.0.0', port=int(server_port))
