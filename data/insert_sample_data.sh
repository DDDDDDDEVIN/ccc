#!/bin/bash

curl -X POST "https://localhost:9200/social_posts/_bulk" \
  -u elastic:<your-password> \
  -H 'Content-Type: application/x-ndjson' \
  --insecure \
  --data-binary @data/cleaned_social_posts_500.ndjson