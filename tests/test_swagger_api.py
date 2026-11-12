import json
import unittest

from flask import Flask

from RestApi.SwaggerApi import register_swagger_ui


class SwaggerApiTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        register_swagger_ui(self.app)
        self.api = self.app.test_client()

    def test_docs_page_is_available_at_offline_url(self):
        response = self.api.get("/offline/docs/", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"swagger-ui-bundle.js", response.data)
        self.assertIn(b"/openapi.json", response.data)
        self.assertNotIn(b"https://", response.data)

    def test_exact_docs_url_redirects_to_ui(self):
        response = self.api.get("/offline/docs")

        self.assertEqual(response.status_code, 308)
        self.assertTrue(response.headers["Location"].endswith("/offline/docs/"))

    def test_openapi_spec_documents_all_api_endpoints(self):
        response = self.api.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        specification = json.loads(response.data)
        response.close()
        self.assertEqual(
            set(specification["paths"]),
            {"/connections", "/connections/{ip_address}", "/measurements/{ip_address}"},
        )
        self.assertEqual(
            set(specification["paths"]["/connections"]),
            {"get", "post"},
        )
        self.assertIn(
            "delete", specification["paths"]["/connections/{ip_address}"]
        )
        self.assertIn(
            "post", specification["paths"]["/measurements/{ip_address}"]
        )
        self.assertEqual(
            {tag["name"] for tag in specification["tags"]},
            {"modbusclient", "measurement"},
        )
        self.assertEqual(
            specification["paths"]["/connections"]["get"]["tags"],
            ["modbusclient"],
        )
        self.assertEqual(
            specification["paths"]["/connections"]["post"]["tags"],
            ["modbusclient"],
        )
        self.assertEqual(
            specification["paths"]["/connections/{ip_address}"]["delete"]["tags"],
            ["modbusclient"],
        )
        self.assertEqual(
            specification["paths"]["/measurements/{ip_address}"]["post"]["tags"],
            ["measurement"],
        )

    def test_swagger_assets_are_served_locally(self):
        response = self.api.get("/offline/docs/swagger-ui-bundle.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.content_type)
        response.close()


if __name__ == "__main__":
    unittest.main()
