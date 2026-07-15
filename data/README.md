# Social Media Sentiment for Australian Election — Elasticsearch Dataset

This repository provides curated and enriched sentiment analysis data collected from Reddit posts about the Australian federal election, structured and ready for Elasticsearch ingestion.

---

## `/data/` folder

| File | Purpose |
|------|---------|
| `sample_social_posts_500.json` | Previewable sample dataset (JSON array, 500 records) |
| `cleaned_social_posts_500.ndjson` | Elasticsearch bulk insert-ready NDJSON format |
| `insert_sample_data.sh` | Shell script to bulk insert NDJSON into Elasticsearch |

---

##`/database/` folder

| File | Purpose |
|------|---------|
| `social_posts_mapping.json` | Elasticsearch index mapping template |
| `create_index.sh` | Shell script to create index with mapping |
| `query_sentiment_by_topic_date.json` | Query template to fetch documents by topic and date |

---

## Usage

### 1. Create Index with Mapping
```bash
bash database/create_index.sh
```

### 2. Insert Sample Data
```bash
bash data/insert_sample_data.sh
```

### 3. Run Query Template
Load the query file in Kibana Dev Tools or with `curl`:
```json
GET social_posts/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "topic": "Labor" }},
        { "match": { "date": "2025-05-01" }}
      ]
    }
  }
}
```
