Architecture du projet :

Le système est basé sur une architecture data moderne combinant ingestion, streaming et stockage.

Flux de données :
API météo → ingestion Python → Kafka → consumer → PostgreSQL → dashboard

Objectifs :
- découpler les composants
- permettre le temps réel
- garantir la scalabilité

Technologies :
- Python
- Kafka
- PostgreSQL
- Docker