from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from rich.console import Console

from .shared import MAX_RETRIES, RETRY_BASE_DELAY, RETRY_STATUS_CODES

console = Console()


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    debug: bool = True,
    **kwargs: Any,
) -> httpx.Response:
    delay = RETRY_BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.request(method, url, **kwargs)
            if debug:
                console.print(f"{response.request.url}")
            if response.status_code in RETRY_STATUS_CODES:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                console.log(f"[yellow]Retry[/yellow] {method} {url} status={response.status_code} attempt={attempt}/{MAX_RETRIES}")
                time.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRY_STATUS_CODES or attempt == MAX_RETRIES:
                raise
            console.log(f"[yellow]Retry[/yellow] {method} {url} status={exc.response.status_code} attempt={attempt}/{MAX_RETRIES}")
            time.sleep(delay)
            delay *= 2
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == MAX_RETRIES:
                raise
            console.log(f"[yellow]Retry[/yellow] {method} {url} attempt={attempt}/{MAX_RETRIES}")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("request_with_retries exhausted all retries")


async def async_request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    debug: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    delay = RETRY_BASE_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if debug:
                console.print(f"{response.request.url}")
            if response.status_code in RETRY_STATUS_CODES:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                console.log(f"[yellow]Retry[/yellow] {method} {url} status={response.status_code} attempt={attempt}/{MAX_RETRIES}")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in RETRY_STATUS_CODES or attempt == MAX_RETRIES:
                raise
            console.log(f"[yellow]Retry[/yellow] {method} {url} status={exc.response.status_code} attempt={attempt}/{MAX_RETRIES}")
            await asyncio.sleep(delay)
            delay *= 2
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == MAX_RETRIES:
                raise
            console.log(f"[yellow]Retry[/yellow] {method} {url} attempt={attempt}/{MAX_RETRIES}")
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("async_request_with_retries exhausted all retries")
