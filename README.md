# AutoPolis

[![Tests](https://github.com/DDDDDDDEVIN/ccc/actions/workflows/tests.yml/badge.svg)](https://github.com/DDDDDDDEVIN/ccc/actions/workflows/tests.yml)

An event-driven cloud pipeline for analysing Australian federal election discourse across Reddit, Mastodon, and Bluesky.

AutoPolis collects public social posts, normalises platform-specific payloads into a shared schema, enriches them with political-party and Australian location labels, and stores the results in Elasticsearch for cross-platform sentiment analysis and visualisation.

> University of Melbourne COMP90024 Cluster and Cloud Computing team project. The deployed university cloud environment is no longer active, but the architecture, infrastructure specifications, tests, sample data, and analysis notebook are preserved in this repository.

## What the project explores

The project was designed around two questions:

1. How has sentiment towards Australian political parties varied by region since the 2022 federal election?
2. Does sentiment towards the same party differ across Reddit, Mastodon, and Bluesky?

The analysis notebook includes post-volume trends, sentiment distributions, party and platform comparisons, word clouds, user-activity analysis, and state-level geographic visualisations.

## Results

The collected dataset contained 22,181 Coalition-related posts, 21,132 Labor-related posts, and 10,663 Greens-related posts. Activity increased sharply around the May 2025 federal election period, with distinct peaks for each political topic.

| Post volume by political topic | Daily posting activity |
| --- | --- |
| ![Horizontal bar chart showing the number of Coalition, Labor, and Greens posts](plots/post-volume-by-party.png) | ![Daily posting trends for Coalition, Labor, and Greens topics during April and May 2025](plots/daily-posting-trends.png) |

Cross-platform analysis showed that sentiment distributions were not uniform. In this dataset, Reddit posts about Labor and the Coalition had higher median sentiment than the corresponding Bluesky and Mastodon posts, while Reddit posts about the Greens were more negative. The heatmap summarises the mean score for every party-platform combination.

| Sentiment distributions across platforms | Mean sentiment by topic and source |
| --- | --- |
| ![Box plots comparing party sentiment across Bluesky, Mastodon, and Reddit](plots/sentiment-by-party-platform.png) | ![Heatmap of mean sentiment by political topic and social platform](plots/sentiment-heatmap.png) |

These are descriptive results from the posts collected by the project's queries and platform APIs. They should not be interpreted as representative estimates of Australian public opinion. Sentiment scores were produced in the analysis notebook rather than by the real-time ingestion functions.

## Architecture

```text
                         ┌──────────────────────┐
                         │ Fission time triggers│
                         └──────────┬───────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        Reddit harvester    Mastodon harvester   Bluesky harvester
                └───────────────────┼───────────────────┘
                                    │ HTTP
                                    ▼
                           ┌─────────────────┐
                           │ enqueue function│
                           └────────┬────────┘
                                    │
                                    ▼
                       Redis platform-specific queues
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        Reddit processor    Mastodon processor   Bluesky processor
                └───────────────────┼───────────────────┘
                                    │ observations queue
                                    ▼
                         addobservations function
                                    │
                                    ▼
                             Elasticsearch
                                    │
                           ┌────────┴────────┐
                           ▼                 ▼
                       REST APIs       Jupyter analysis
```

Fission time triggers invoke each harvester at a platform-appropriate interval. Harvesters send batches through an HTTP enqueue function, which routes them to Redis lists. KEDA-backed Fission message-queue triggers scale the corresponding processors and forward their normalised output to the `observations` queue. A final function indexes each observation in Elasticsearch using a deterministic document ID.

Redis also stores platform cursors and deduplication state so repeated harvesting does not continually reprocess the same posts.

## Technology stack

| Area | Technologies |
| --- | --- |
| Cloud runtime | Kubernetes, Fission, KEDA |
| Event pipeline | Redis lists and message-queue triggers |
| Data sources | Reddit API/PRAW, Mastodon API, Bluesky/AT Protocol |
| Backend | Python, Flask |
| Search and storage | Elasticsearch 8, Kibana |
| Analysis | Pandas, Transformers, VADER, GeoPandas |
| Visualisation | Matplotlib, Seaborn, Plotly, WordCloud |
| Testing | `unittest`, Flask test client, mocks |

## Data model and enrichment

All three processors produce the same observation shape:

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

Topic aliases are mapped to the canonical categories `labor`, `coalition`, and `greens`. Location enrichment searches post content—and Reddit community metadata where available—for Australian state, territory, and major-city aliases.

## Repository map

```text
backend/fission/functions/   Fission harvesters, processors, queue and API functions
backend/fission/specs/       Kubernetes/Fission functions, packages and trigger specs
database/                    Elasticsearch mapping and query examples
data/                        500-record anonymised sample and bulk-import files
frontend/frontend.ipynb      Sentiment analysis and interactive visualisations
plots/                       Static plot outputs exported from the notebook
test/                        Unit and mocked end-to-end tests
docs/                        Original project report
```

Key implementation areas:

- `*harvester`: platform API access, cursors, batching, and deduplication.
- `enqueue`: HTTP-to-Redis topic routing.
- `*processor`: schema normalisation, topic mapping, and location extraction.
- `addobservations`: deterministic indexing into Elasticsearch.
- `countposts`: date- and topic-filtered post counts.
- `es-api`: optional standalone Elasticsearch health, index listing, and scroll-search service.

## Running the analysis locally

The cloud ingestion pipeline requires Kubernetes, Fission, Redis, Elasticsearch, and valid platform credentials. The analysis can instead be explored independently using the included sample data and notebook.

```bash
conda create -n autopolis python=3.10 -y
conda activate autopolis
conda install -c conda-forge geopandas ipywidgets -y
pip install pandas plotly seaborn matplotlib wordcloud transformers nltk requests
jupyter notebook frontend/frontend.ipynb
```

The notebook defaults to `http://localhost:8888/es-api/scroll_search`. Point it to a deployed query service without editing the notebook:

```bash
export AUTOPOLIS_API_URL="https://your-api.example/es-api/scroll_search"
jupyter notebook frontend/frontend.ipynb
```

Alternatively, replace its API-loading cell with the sample dataset in `data/sample_social_posts_500.json`.

### Optional Elasticsearch query API

`backend/fission/functions/es-api` is a standalone optional query service with health, index-listing, and scroll-search endpoints. Its `function.yaml` and `trigger.yaml` are reference deployment manifests and are not applied by the primary `backend/fission/specs` application. The ingestion pipeline and date/topic count routes do not depend on this service.

## Deploying the Fission pipeline

Prerequisites:

- a Kubernetes cluster with Fission and its KEDA Redis MQ integration;
- Redis reachable at the in-cluster address configured by the functions;
- Elasticsearch 8;
- `kubectl` and the Fission CLI;
- API credentials for the selected social platforms.

Create runtime credentials as Kubernetes Secrets. Replace every placeholder locally; do not commit real values.

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

Apply the Fission specifications from the `backend` directory so the package include paths resolve correctly:

```bash
cd backend
fission spec apply --specdir fission/specs --wait
```

Example query routes after forwarding the Fission router:

```bash
kubectl port-forward service/router -n fission 9090:80
curl http://localhost:9090/posts/days/2025-05-10
curl http://localhost:9090/posts/days/2025-05-10/topics/greens
```

## Tests

Tests isolate external services with mocks and cover payload validation, platform normalisation, location and topic extraction, Redis enqueue behaviour, Elasticsearch indexing, and a function-level end-to-end flow.

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s test -v
```

Function deployment dependencies remain in each Fission package's `requirements.txt`; `requirements-dev.txt` provides one installation entry point for local development and CI.

## Team and attribution

AutoPolis was developed by a five-person team for the University of Melbourne:

- Devin (Angqi) Meng
- Yichen Long
- Xuan Wu
- Zining Zhang
- Jingqiu Meng

### Portfolio contribution

**Devin (Angqi) Meng** designed and helped build the end-to-end system architecture. His work focused on:

- designing the event-driven ingestion and processing pipeline;
- implementing social-platform harvesters, including API integration, cursor management, batching, and deduplication;
- implementing processors that normalise platform payloads and enrich posts with political-topic and Australian-location metadata;
- provisioning and configuring the cloud environment, including Kubernetes, Fission, Redis, Elasticsearch, and the functions' triggers and deployment specifications;
- integrating the pipeline's components from collection through queue-based processing to persistent storage.

GitHub Actions runs the complete test suite on every pull request and every push to `main`. This CI workflow was added while preparing the original project for portfolio publication and was not part of the university deployment.

The original submission report is available in `docs/COMP90024_team_60_report.pdf`.
