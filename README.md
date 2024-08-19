# Transferring Opsgenie Alerts to Elasticsearch and Cortex for Customized Dashboarding
## Project Purpose: Alert Consolidation and Analysis

The purpose of this project is to consolidate alerts coming to Opsgenie from various sources and make them available for comprehensive analysis. Currently, alerts are triggered from a couple of sources, like Prometheus Alertmanager and Google Beam jobs. Although all alerts are directed to Opsgenie, where there are some built-in dashboards, the objective is to move these alerts to Elasticsearch or Cortex (TSDB) for customized dashboarding and deeper analysis.

Solution: Leveraging the opsgenie webhook integration, we redirect all the alerts to a Python Flask app, which customizes the alert data and publishes it to Cortex and to Elasticsearch. The timeseries data in Cortex can then be used to build dashboards and the alerts in Elasticsearch can be used to make dashboards using Apache Superset.

Dashboard in Superset:

<img width="1000" alt="Screenshot 2024-08-12 at 10 17 13 PM" src="https://github.com/user-attachments/assets/b8cc48bb-a85a-4d67-a43e-d15140fe18e0">


Dashboard in Kibana:


<img width="1784" alt="Screenshot 2024-06-29 at 12 55 54 PM" src="https://github.com/user-attachments/assets/5041590c-67c2-47a6-9c30-5b967e4785b6">
<img width="1725" alt="Screenshot 2024-06-29 at 12 56 34 PM" src="https://github.com/user-attachments/assets/988a93ee-724c-4ad2-a34a-bf7e351ff887">

<br>
<br>
Similarly, dashboards in Grafana can be built using the alerts in Cortex.

Initially, I set up this project using AWS SNS (Simple Notification Service) and Lambda. This was the workflow:

However, since we needed Elasticsearch to be setup in a GKE (Google Kubernetes Engine) cluster, we had to migrate the setup to GCP. Opsgenie does not have a direct integration with GCP. So, we had to use Opsgenie's Webhook integration to send alert updates to a Cloud Run service in GCP. The Cloud Run service then directly processes the alerts and writes them to the Elasticsearch cluster in GKE. This eliminated the need to use the Google Pub/Sub, which is the equivalent of AWS SNS. The new workflow is the following:

## Steps
#### 1. Set up OpsGenie
![image](https://github.com/user-attachments/assets/85e7f811-334a-4aef-ad7c-bb59a3b139b0)
