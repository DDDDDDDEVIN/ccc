# COMP90024 Team 60 - AutoPolis: Read-Time Social Media Sentiment Analysis for Australian Election Discourse

This repository contains the implementation for Assignment 2 of COMP90024 at the University of Melbourne. The project focuses on big data analytics using real-time and historical data harvesting from social media platforms relevant to Australian public discourse.

## Team Members

- Angqi Meng – 1268867
- Yichen Long – 1497321
- Xuan Wu – 1483104
- Zining Zhang – 1508501
- Jingqiu Meng – 1506602

## Project Overview

This cloud-based system used Kubernetes, Fission, and ElasticSearch to stream and analyze social media data from Reddit, Bluesky, and Mastodon. It extracts insights using sentiment analysis and geolocation tagging, exposing the results via a RESTful API and visualizing them in a Jupyter Notebook frontend.

# Scenarios:
(1) How does the sentiment of different regions for different parties change since 2022 election?

(2) Is the sentiment of Australians for the particular parties the same across Mastodon, Bluesky and Reddit?

## Architecture

```text
Timer Trigger (Harvester) ──▶ HTTP Trigger (Enqueue) ──▶ MQ Trigger (Processor) ──▶ MQ Trigger (AddObservations) ──▶ ElasticSearch ──▶ HTTP Trigger (RESTful API) ──▶ Jupyter Notebook
```

### Components
- **Harvesters**: Platform-specific harvesters triggered at custom intervals (e.g. 20s for Bluesky).
- **Processors**: Extract metadata like `created_at`, `text`, `tags`, `user_id`, `location`.
- **Redis**: Used for message queuing between functions and for tracking cursors and deduplication.
- **ElasticSearch**: Central storage for processed observations.
- **RESTful API**: Provides endpoint access to the indexed data.
- **Kibana**: Used for dashboard and geographic data visualization.
- **Jupyter Notebook**: Final data analytics and visualization tool for scenario evaluation.

### Deployment Steps
```bash
# 1. Apply Fission specs

(cd backend
cd functions
fission spec apply --specdir fission/specs --wait .)


# 2. Monitor function logs
fission fn logs -f --name {function-name}

# 3. Monitor pods activities
kubectl get pods -n fission

# 4. Monitor nodes usage
kubectl top nodes

# 5. Restful API usage
kubectl port-forward service/router -n fission 9090:80
curl http://localhost:9090/posts/days/2025-05-10 | jq '.'
curl http://localhost:9090/posts/days/2025-05-10/topics/greens | jq '.'

```

## Code Layout
```
README.md              - Project overview, setup instructions, and how to run the system

frontend/              - Jupyter notebooks for:
                         - Visualising post volumes, topics, and trends
                         - Map visualisations

backend/               - Server-side logic and deployment files
│
├── fission/           - All Fission-related source code and specs
│   │
│   ├── functions/     - Python functions deployed with Fission
│   │   ├── bharvester-h/   - BlueSky historical post harvester
│   │   ├── mharvester/     - Mastodon harvester
│   │   ├── rharvester/     - Reddit harvester
│   │   ├── enqueue/        - Redis message enqueue function
│   │   ├── bprocessor/     - BlueSky post processor
│   │   ├── mprocessor/     - Mastodon post processor
│   │   ├── rprocessor/     - Reddit post processor
│   │   ├── addobservations/ - Function that writes posts to ElasticSearch
│   │   └── postscount/        - ReSTful API to query post volume in a given date with given topic (optional)
│   │
│   └── specs/         - Fission YAML spec files (used with `fission spec apply`)
│       ├── function-*.yaml       - Definitions for all 9 functions
│       ├── package-*.yaml        - Fission packages including source archives and build commands
│       ├── route-*.yaml          - HTTP trigger routes (ReSTful API endpoints)
│       ├── timetrigger-*.yaml    - Timer-based triggers for periodic harvesting
│       ├── mqtrigger-*.yaml      - Redis queue triggers for function chaining
│       ├── configmap.yaml        - ConfigMap for secrets and runtime parameters
│       └── .specignore           - Ignore list to exclude files from spec validation

test/                  - Unit and integration tests using `unittest`
                         - Test coverage for processors, enqueue logic, and API response validation

database/              - ElasticSearch type mappings

data/                  - Optional: static files or sample JSON used for test ingestion

docs/                  - Final project report

```

## Testing
```bash
# 1. Unit Test
python -m unittest test.test_bprocessor
python -m unittest test.test_enqueue
python -m unittest test.test_mprocessor
python -m unittest test.test_rprocessor
python -m unittest test.test_addobservations

# 2. End-to-end Test
python -m unittest test.test_end_to_end
```
---