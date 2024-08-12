# opsgenie-to-es-and-cortex
Project Purpose: Alert Consolidation and Analysis

The purpose of this project is to consolidate alerts coming to Opsgenie from various sources and make them available for comprehensive analysis. Currently, alerts are triggered from a couple of sources, namely Prometheus Alertmanager and Google Beam jobs. Although all alerts are directed to Opsgenie, where we have some built-in dashboards, the objective is to move these alerts to Elasticsearch or Cortex (TSDB) for customized dashboarding and deeper analysis.
Project Purpose: Alert Consolidation and Analysis

Solution: Leaveraging opsgenie integrations we redirect all the alerts to a python webhook which does some customization on the alert data and publish it to cortex in time series format and to elasticsearch. 
![image](https://github.com/user-attachments/assets/85e7f811-334a-4aef-ad7c-bb59a3b139b0)
