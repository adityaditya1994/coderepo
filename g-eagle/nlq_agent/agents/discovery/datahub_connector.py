"""
DataHub connector — queries DataHub's GraphQL API
for dataset metadata matching a user query.
"""

import requests
from typing import List


class DataHubConnector:
    """Search DataHub for relevant datasets via GraphQL."""

    def __init__(self, config: dict):
        self.gms_url = config.get("DATAHUB_GMS_URL", "http://localhost:8080")
        self.token = config.get("DATAHUB_TOKEN", "")

    def search(self, query: str, count: int = 10) -> List[dict]:
        """
        Search DataHub for datasets matching the query.

        Returns
        -------
        list[dict]
            Normalized table metadata dicts.
        """
        graphql_url = f"{self.gms_url}/api/graphql"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        graphql_query = """
        query search($input: SearchInput!) {
          search(input: $input) {
            searchResults {
              entity {
                urn
                type
                ... on Dataset {
                  name
                  platform { name }
                  editableSchemaMetadata {
                    editableSchemaFieldInfo {
                      fieldPath
                    }
                  }
                  schemaMetadata {
                    fields {
                      fieldPath
                      nativeDataType
                      description
                    }
                  }
                  editableProperties {
                    description
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "input": {
                "type": "DATASET",
                "query": query,
                "start": 0,
                "count": count,
            }
        }

        try:
            resp = requests.post(
                graphql_url,
                json={"query": graphql_query, "variables": variables},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        results = []
        search_results = (
            data.get("data", {})
                .get("search", {})
                .get("searchResults", [])
        )

        for sr in search_results:
            entity = sr.get("entity", {})
            schema_meta = entity.get("schemaMetadata", {})
            fields = schema_meta.get("fields", []) if schema_meta else []
            editable_props = entity.get("editableProperties", {})

            columns = [
                {
                    "name": f.get("fieldPath", ""),
                    "type": f.get("nativeDataType", ""),
                }
                for f in fields
            ]

            results.append({
                "source": "datahub",
                "name": entity.get("name", ""),
                "database": "",
                "columns": columns,
                "description": (
                    editable_props.get("description", "")
                    if editable_props else ""
                ),
            })

        return results
