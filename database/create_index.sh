#!/bin/bash

curl -X PUT "https://localhost:9200/social_posts" \
  -u elastic:<your-password> \
  -H 'Content-Type: application/json' \
  --insecure \
  -d @database/social_posts_mapping.json

