import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests


def load_es_api_module():
    """Load the standalone ES API whose directory name contains a hyphen."""
    module_path = (
        Path(__file__).parent.parent
        / "backend/fission/functions/es-api/es_api.py"
    )
    spec = importlib.util.spec_from_file_location("es_api_function", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


es_api = load_es_api_module()


def mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class TestEsApi(unittest.TestCase):
    def setUp(self):
        self.client = es_api.app.test_client()
        self.es_config = {
            "url": "https://elasticsearch.test:9200",
            "auth": ("user", "password"),
            "headers": {"Content-Type": "application/json"},
            "verify": False,
            "timeout": 5,
        }
        self.config_patcher = patch.object(
            es_api, "get_es_connection", return_value=self.es_config
        )
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()

    @patch.object(es_api.requests, "get")
    def test_health_endpoint(self, mock_get):
        mock_get.return_value = mock_response({"status": "green"})

        response = self.client.get("/es-api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["status"], "green")
        mock_get.assert_called_once_with(
            "https://elasticsearch.test:9200/_cluster/health",
            auth=("user", "password"),
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=5,
        )

    @patch.object(es_api.requests, "get")
    def test_indices_endpoint(self, mock_get):
        mock_get.return_value = mock_response(
            [{"index": "observations"}, {"index": "other"}]
        )

        response = self.client.get("/es-api/indices")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], ["observations", "other"])

    def test_scroll_search_requires_index_for_initial_request(self):
        response = self.client.get("/es-api/scroll_search")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["message"],
            "Missing required parameter: index",
        )

    @patch.object(es_api.requests, "post")
    def test_scroll_search_starts_match_all_query(self, mock_post):
        mock_post.return_value = mock_response(
            {
                "_scroll_id": "scroll-1",
                "hits": {"hits": [{"_source": {"post_id": "123"}}]},
            }
        )

        response = self.client.get(
            "/es-api/scroll_search",
            query_string={"index": "observations", "scroll": "2m"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["scroll_id"], "scroll-1")
        self.assertEqual(response.get_json()["data"], [{"post_id": "123"}])
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["query"], {"match_all": {}})
        self.assertIn("/observations/_search?scroll=2m", mock_post.call_args.args[0])

    @patch.object(es_api.requests, "post")
    def test_scroll_search_supports_term_query(self, mock_post):
        mock_post.return_value = mock_response(
            {"_scroll_id": "scroll-1", "hits": {"hits": []}}
        )

        response = self.client.get(
            "/es-api/scroll_search",
            query_string={
                "index": "observations",
                "field": "source.keyword",
                "value": "reddit",
            },
        )

        self.assertEqual(response.status_code, 200)
        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["json"]["query"],
            {"term": {"source.keyword": {"value": "reddit"}}},
        )

    @patch.object(es_api.requests, "post")
    def test_scroll_search_continues_with_scroll_id(self, mock_post):
        mock_post.return_value = mock_response(
            {"_scroll_id": "scroll-2", "hits": {"hits": []}}
        )

        response = self.client.get(
            "/es-api/scroll_search",
            query_string={"scroll_id": "scroll-1", "scroll": "2m"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://elasticsearch.test:9200/_search/scroll",
        )
        self.assertEqual(
            mock_post.call_args.kwargs["json"],
            {"scroll": "2m", "scroll_id": "scroll-1"},
        )

    @patch.object(es_api.requests, "get")
    def test_upstream_failure_returns_500(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("unavailable")

        response = self.client.get("/es-api/health")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["status"], "error")
        self.assertIn("unavailable", response.get_json()["message"])


if __name__ == "__main__":
    unittest.main()
