# AutoPolis Social Analytics

[![Tests](https://github.com/DDDDDDDEVIN/autopolis-social-analytics/actions/workflows/tests.yml/badge.svg)](https://github.com/DDDDDDDEVIN/autopolis-social-analytics/actions/workflows/tests.yml)

An end-to-end, event-driven cloud analytics project that collects Australian
federal election discourse from Reddit, Mastodon, and Bluesky, enriches posts
with political-topic and location labels, and compares sentiment across
platforms and regions.

> **Academic team project:** This repository is a portfolio edition of a group
> project completed for COMP90024 Cluster and Cloud Computing at the University
> of Melbourne in 2025. It preserves the original cloud architecture, analysis,
> deployment specifications, tests, and sample data. The university cloud
> environment is no longer active, and the results should not be interpreted as
> current or representative measures of Australian public opinion.

**Portfolio owner and maintainer:** Devin (Angqi) Meng

![Daily posting trends by political party](plots/daily-posting-trends.png)

## Project overview

The project was designed to answer two questions:

1. How has sentiment towards Australian political parties varied by region
   since the 2022 federal election?
2. Does sentiment towards the same party differ across Reddit, Mastodon, and
   Bluesky?

The workflow covers platform API collection, cursor-based harvesting,
queue-driven processing, schema normalisation, topic and location enrichment,
Elasticsearch storage, sentiment analysis, and interactive visualisation.

## Highlights

- Collected 53,976 election-related posts across three social platforms,
  including 22,181 Coalition, 21,132 Labor, and 10,663 Greens observations.
- Designed a Kubernetes and Fission pipeline with time triggers, HTTP
  functions, Redis queues, and KEDA-backed message-queue triggers.
- Implemented platform-specific cursor management, batching, and deduplication
  for Reddit, Mastodon, and Bluesky.
- Normalised different platform payloads into a shared observation model and
  enriched posts with political-topic and Australian state or territory labels.
- Compared posting activity and sentiment distributions across parties,
  platforms, regions, and user-activity segments.
- Added GitHub Actions CI with 40 unit and mocked integration tests.

In the collected dataset, Reddit posts about Labor and the Coalition had higher
median sentiment than the corresponding Bluesky and Mastodon posts, while
Reddit posts about the Greens were more negative. These are descriptive results
from the project's queries and platform APIs, not population estimates.

## Selected outputs

| Post volume | Daily activity | Platform comparison | Sentiment heatmap |
| --- | --- | --- | --- |
| [Party volumes](plots/post-volume-by-party.png) | [Posting trends](plots/daily-posting-trends.png) | [Sentiment distributions](plots/sentiment-by-party-platform.png) | [Topic and source](plots/sentiment-heatmap.png) |

Additional sentiment and user-segment plots are available in
[`plots/`](plots/).

## Data pipeline

```text
                         Fission time triggers
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
        Reddit harvester  Mastodon harvester  Bluesky harvester
                +-----------------+-----------------+
                                  | HTTP
                                  v
                           Enqueue function
                                  |
                                  v
                    Redis platform-specific queues
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
        Reddit processor  Mastodon processor  Bluesky processor
                +-----------------+-----------------+
                                  | observations queue
                                  v
                       Add-observations function
                                  |
                                  v
                           Elasticsearch
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                     REST APIs       Jupyter analysis
```

Fission time triggers invoke each harvester at a platform-appropriate interval.
Harvesters send batches through an HTTP enqueue function, which routes them to
Redis lists. KEDA-backed Fission triggers scale the corresponding processors
and forward normalised output to the `observations` queue. A final function
indexes each observation in Elasticsearch with a deterministic document ID.
Redis also stores cursors and deduplication state to avoid repeatedly processing
the same posts.

## Repository structure

```text
.
├── backend/fission/functions/   Harvesters, processors, queue and API functions
├── backend/fission/specs/       Fission functions, packages, configs and triggers
├── database/                    Elasticsearch mapping and query examples
├── data/                        Sample observations and bulk-import files
├── frontend/                    Sentiment analysis and visualisation notebook
├── plots/                       Portfolio-ready static outputs
├── test/                        Unit and mocked end-to-end tests
└── docs/                        Original project report
```

Function deployment dependencies are kept in each Fission package's
`requirements.txt`. The root `requirements-dev.txt` provides one installation
entry point for local backend development and CI.

## Reproducing the analysis

The notebook reflects the original coursework analysis. Its default data source
is the optional Elasticsearch query API at
`http://localhost:8888/es-api/scroll_search`; a full rerun therefore requires a
compatible Elasticsearch deployment or an adjustment to the first loading
cell. The included sample dataset can be used for lightweight local exploration.

Create an isolated environment and install the analysis dependencies:

```bash
conda create -n autopolis python=3.10 -y
conda activate autopolis
conda install -c conda-forge geopandas ipywidgets -y
pip install pandas plotly seaborn matplotlib wordcloud transformers nltk requests
jupyter notebook frontend/frontend.ipynb
```

Point the notebook to another deployment without editing it:

```bash
export AUTOPOLIS_API_URL="https://your-api.example/es-api/scroll_search"
jupyter notebook frontend/frontend.ipynb
```

Alternatively, replace the API-loading cell with
`data/sample_social_posts_500.json`.

### Optional Elasticsearch query API

`backend/fission/functions/es-api` is a standalone optional service providing
health, index-listing, and scroll-search endpoints. Its `function.yaml` and
`trigger.yaml` are reference manifests and are not applied by the primary
`backend/fission/specs` application. The ingestion pipeline and date/topic
count routes do not depend on this service.

## Methods

- **Data collection:** platform-specific harvesters query Reddit, Mastodon, and
  Bluesky on independent schedules, using Redis-backed cursors and seen-ID sets.
- **Event processing:** an HTTP function routes batches into Redis lists, while
  Fission MQ triggers invoke and scale the relevant processor.
- **Normalisation:** processors convert each platform payload into a shared
  schema containing timestamps, text, source, tags, IDs, topic, and location.
- **Enrichment:** configured keyword aliases map posts to Labor, Coalition, or
  Greens topics and infer Australian states or territories from post content
  and Reddit community metadata.
- **Storage and access:** processed observations are indexed in Elasticsearch;
  REST functions provide count and optional scroll-search access.
- **Analysis:** the Jupyter workflow uses Transformers and VADER sentiment
  analysis with Pandas, GeoPandas, Matplotlib, Seaborn, and Plotly outputs.

### Observation model

All three processors produce the same core document shape:

```json
{
  "created_at": "2025-05-01T09:30:00Z",
  "text": "Example social post",
  "location": "VIC",
  "source": "mastodon",
  "tags": ["auspol"],
  "post_id": "platform-specific-id",
  "user_id": "platform-specific-user",
  "topic": "labor"
}
```

## Deploying the Fission pipeline

Deployment requires Kubernetes with Fission and its KEDA Redis MQ integration,
an in-cluster Redis service, Elasticsearch 8, `kubectl`, the Fission CLI, and
credentials for the selected social platforms.

Create credentials as Kubernetes Secrets. Replace every placeholder locally and
do not commit real values:

```bash
kubectl create secret generic reddit-credentials \
  --from-literal=REDDIT_CLIENT_ID='<reddit-client-id>' \
  --from-literal=REDDIT_CLIENT_SECRET='<reddit-client-secret>'

kubectl create secret generic bluesky-credentials \
  --from-literal=BSKY_USERNAME='<bluesky-username>' \
  --from-literal=BSKY_PASSWORD='<bluesky-app-password>'

kubectl create secret generic mastodon-credentials \
  --from-literal=MASTODON_TOKEN='<mastodon-access-token>'

kubectl create secret generic es-credentials \
  --from-literal=ES_USERNAME='<elasticsearch-username>' \
  --from-literal=ES_PASSWORD='<elasticsearch-password>'
```

Apply the primary Fission specifications from the `backend` directory so the
package include paths resolve correctly:

```bash
cd backend
fission spec apply --specdir fission/specs --wait
```

Example count queries after forwarding the Fission router:

```bash
kubectl port-forward service/router -n fission 9090:80
curl http://localhost:9090/posts/days/2025-05-10
curl http://localhost:9090/posts/days/2025-05-10/topics/greens
```

## Tests

Tests isolate external services with mocks and cover payload validation,
platform normalisation, location and topic extraction, Redis enqueue behaviour,
Elasticsearch indexing and querying, harvesters, and a function-level
end-to-end flow.

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s test -v
```

GitHub Actions runs the complete 40-test suite on every pull request and every
push to `main`.

## Limitations and responsible use

- Platform APIs, authentication requirements, and response schemas may have
  changed since the original 2025 deployment.
- Collection was driven by selected keywords, hashtags, and communities, so the
  dataset is not a representative sample of Australian voters or social media.
- Location labels are inferred from textual aliases rather than verified user
  locations and may be missing or incorrect.
- Sentiment models can misinterpret sarcasm, political language, and contextual
  references; scores should be treated as exploratory signals.
- The original university cloud environment is no longer active, and deployment
  manifests may require version updates for a new cluster.
- Any renewed collection should comply with each platform's current terms,
  privacy requirements, and rate limits.

## My contribution

Devin (Angqi) Meng designed and helped build the end-to-end system architecture.
His technical contributions included:

- designing the event-driven ingestion and processing pipeline;
- implementing social-platform harvesters, including API integration, cursor
  management, batching, and deduplication;
- implementing processors that normalise platform payloads and enrich posts
  with political-topic and Australian-location metadata;
- provisioning and configuring Kubernetes, Fission, Redis, Elasticsearch,
  function triggers, and deployment specifications;
- integrating the system from collection through queue-based processing to
  persistent storage; and
- configuring CI to run the project's test suite on every pull request and
  push to `main`.

The work was completed collaboratively, and other team members contributed to
the broader pipeline, analysis, visualisation, testing, and project delivery.

## Team and attribution

This work was completed by COMP90024 Team 60: Devin (Angqi) Meng, Yichen Long,
Xuan Wu, Zining Zhang, and Jingqiu Meng. The repository is shared as an academic
portfolio artefact; platform content and third-party services remain subject to
their respective licences and terms.

The original submission report is available at
[`docs/COMP90024_team_60_report.pdf`](docs/COMP90024_team_60_report.pdf).

## Technology

Python, Flask, Kubernetes, Fission, KEDA, Redis, Elasticsearch, Kibana, Reddit
API/PRAW, Mastodon API, Bluesky/AT Protocol, Jupyter, Pandas, Transformers,
VADER, GeoPandas, Matplotlib, Seaborn, Plotly, WordCloud, and GitHub Actions.
