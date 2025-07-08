"""
title: Vanna Pipeline
author: Nichi
author_url: Your URL (e.g., https://github.com/nichiyoo)
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
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        if self.valves.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

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
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        logger.info("pipe: %s" % self.name)

        if self.valves.DEBUG:
            logger.debug(
                "pipe: %s - received message from user: %s" % (self.name, user_message)
            )

        try:
            sql_text = _generate_sql_from_vanna(
                api_url=self.valves.API_URL,
                question=user_message,
                verify_ssl=self.valves.VERIFY_SSL,
            )

            yield "```sql\n%s\n```" % sql_text
        except Exception as e:
            logger.exception("Vanna: An error occurred during SQL generation: %s" % e)
            yield "Vanna: An error occurred while generating SQL. Please try again."


def _generate_sql_from_vanna(api_url: str, question: str, verify_ssl: bool) -> str:
    """
    Generates an SQL query by sending a natural language question to the Vanna backend.

    Args:
        api_url (str): The base URL of the Vanna backend.
        question (str): The natural language question to generate SQL for.
        verify_ssl (bool): Whether to verify SSL certificates for the request.

    Returns:
        str: The generated SQL query.

    Raises:
        requests.exceptions.RequestException: For any HTTP or connection errors.
        json.JSONDecodeError: If the response is not valid JSON.
        ValueError: If the 'text' field is missing from the Vanna response.
    """
    generate_sql_endpoint = urljoin(api_url, "/api/generate_sql")
    params = {"question": question}

    response = requests.get(generate_sql_endpoint, params=params, verify=verify_ssl)
    response.raise_for_status()

    sql_response = response.json()

    if "text" in sql_response:
        return sql_response["text"]
    else:
        raise ValueError("Vanna: 'text' field missing from response.")
