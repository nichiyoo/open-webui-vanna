"""
title: Vanna Pipeline
author: Nichi
author_url: https://github.com/nichiyoo
description: Generates SQL queries from natural language questions using a Vanna backend.
required_open_webui_version: 0.4.3
requirements: requests
version: 0.4.3
licence: MIT
"""

import os
import requests
import logging
from pprint import pprint
from urllib.parse import urljoin
from pydantic import BaseModel, Field
from typing import List, Union, Generator, Iterator, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _generate_sql_from_vanna(api_url: str, question: str, verify_ssl: bool) -> dict:
    """
    Generates an SQL query by sending a natural language question to the Vanna backend.

    Args:
        api_url (str): The base URL of the Vanna backend.
        question (str): The natural language question to generate SQL for.
        verify_ssl (bool): Whether to verify SSL certificates for the request.

    Returns:
        dict: The JSON response from the Vanna API, expected to contain 'text' and 'id'.

    Raises:
        requests.exceptions.RequestException: For any HTTP or connection errors.
        requests.exceptions.HTTPStatusError: For bad HTTP responses (4xx or 5xx).
        json.JSONDecodeError: If the response is not valid JSON.
        ValueError: If the 'text' or 'id' field is missing from the Vanna response.
    """
    endpoint = urljoin(api_url, "/api/generate_sql")
    params = {
        "question": question,
    }

    response = requests.get(endpoint, params=params, verify=verify_ssl)
    response.raise_for_status()

    sql_response = response.json()
    if "text" in sql_response and "id" in sql_response:
        return sql_response
    else:
        raise ValueError(
            "Vanna: Invalid response from SQL generation service. Missing 'text' or 'id'."
        )


def _run_sql_query(api_url: str, cache_id: str, verify_ssl: bool) -> str:
    """
    Executes an SQL query using the Vanna backend's run_sql endpoint.

    Args:
        api_url (str): The base URL of the Vanna backend.
        cache_id (str): The cache ID of the generated SQL query.
        verify_ssl (bool): Whether to verify SSL certificates for the request.

    Returns:
        str: The DataFrame result as a string.

    Raises:
        requests.exceptions.RequestException: For any HTTP or connection errors.
        requests.exceptions.HTTPStatusError: For bad HTTP responses (4xx or 5xx).
        json.JSONDecodeError: If the response is not valid JSON.
        ValueError: If the 'df' field is missing from the Vanna response.
    """
    endpoint = urljoin(api_url, "/api/run_sql")
    params = {
        "id": cache_id,
    }

    response = requests.get(endpoint, params=params, verify=verify_ssl)
    response.raise_for_status()

    df_response = response.json()
    if "df" in df_response:
        return df_response["df"]
    else:
        raise ValueError("Vanna: 'df' field missing from run_sql response.")


class Pipeline:
    class Valves(BaseModel):
        API_URL: str = Field(
            default="http://host.docker.internal:4321",
            description="The base URL of your Vanna backend. ",
        )
        VERIFY_SSL: bool = Field(
            default=True,
            description="Set to False to disable SSL verification.",
        )
        DEBUG: bool = Field(
            default=False,
            description="Enable debug logging for the pipeline.",
        )

    def __init__(self):
        self.name = "Vanna Pipeline"
        fields = self.Valves.model_fields.items()
        self.valves = self.Valves(**{k: os.getenv(k, v.default) for k, v in fields})
        logger.setLevel(logging.DEBUG if self.valves.DEBUG else logging.INFO)

    async def on_startup(self):
        logger.info("on_startup: %s" % self.name)
        pass

    async def on_shutdown(self):
        logger.info("on_shutdown: %s" % self.name)
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        logger.debug("inlet: %s" % self.name)
        if self.valves.DEBUG:
            logger.debug("inlet: %s - body:" % self.name)
            pprint(body)
            logger.debug("inlet: %s - user:" % self.name)
            pprint(user)
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        logger.debug("outlet: %s" % self.name)
        if self.valves.DEBUG:
            logger.debug("outlet: %s - body:" % self.name)
            pprint(body)
            logger.debug("outlet: %s - user:" % self.name)
            pprint(user)
        return body

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        logger.info("pipe: %s" % self.name)

        if self.valves.DEBUG:
            logger.debug(
                "pipe: %s - received message from user: %s" % (self.name, user_message)
            )

        try:
            yield {
                "event": {
                    "type": "status",
                    "data": {"description": "Vanna: Generating SQL...", "done": False},
                }
            }

            vanna_response = _generate_sql_from_vanna(
                api_url=self.valves.API_URL,
                question=user_message,
                verify_ssl=self.valves.VERIFY_SSL,
            )
            sql_text = vanna_response["text"]
            cache_id = vanna_response["id"]

            yield "```sql\n%s\n```" % sql_text

            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "Vanna: Running SQL query...",
                        "done": False,
                    },
                }
            }

            df_result = _run_sql_query(
                api_url=self.valves.API_URL,
                cache_id=cache_id,
                verify_ssl=self.valves.VERIFY_SSL,
            )

            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "Vanna: SQL execution complete.",
                        "done": True,
                    },
                }
            }

            yield "\n```json\n%s\n```" % df_result

        except Exception as e:
            logger.exception(
                "Vanna: An error occurred during SQL generation/execution: %s" % e
            )

            yield {
                "event": {
                    "type": "status",
                    "data": {
                        "description": "Vanna: Error during SQL process.",
                        "done": True,
                    },
                }
            }

            yield "Vanna: An error occurred while generating or executing SQL. Please try again."
