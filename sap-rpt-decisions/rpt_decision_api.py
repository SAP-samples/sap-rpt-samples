"""
A sample client for the sap-rpt-decisions model.

The Decision API builds on the RPT model. You give it
a ``state`` to evaluate, a set of ``questions``, and some labeled ``examples`` to learn
from; it answers each question. Three question types are supported:

  * ``noul``   — a yes/no (boolean) question; the answer is P(true),
  * ``choice`` — pick one option from a set; the answer is the selected option,
  * ``score``  — rate on an ordered scale; the answer is a probability-weighted score.

sap-rpt-decisions is an in-context model and cannot answer zero-shot, so at least two labeled
``examples`` are required. Each example mirrors the request ``state`` and carries an
``answers`` map holding the known answer for every question.

Usage
-----
    from rpt_decision_api import RptDecisionClient, noul, choice, score

    client = RptDecisionClient(url="https://<host>/systemone")  # auth is lazy
    answers = client.ask(
        state={"product": "4K Monitor", "price": 350},
        questions={
            "category": choice(
                "Which category?",
                {"Electronics": "Powered devices", "Accessories": "Add-ons"},
            ),
            "is_premium": noul("Is this a premium product?"),
            "value_rating": score("Rate the value.", ["Low", "High"]),
        },
        # Every declared option/level must appear as an answer in at least one example.
        examples=[
            {"state": {"product": "Gaming Laptop", "price": 1899},
             "answers": {"category": "Electronics", "is_premium": True, "value_rating": 1}},
            {"state": {"product": "USB Mouse", "price": 15},
             "answers": {"category": "Accessories", "is_premium": False, "value_rating": 0}},
        ],
    )
    print(answers["category"].choice, answers["is_premium"].noul)

Only ``httpx`` is required (``pip install httpx``). Authentication uses the BTP AI Core
client-credentials flow and is inlined. Set the
``AICORE_SERVICE_KEY`` environment variable to the AI Core service-key JSON before use.

Requests are scoped to an AI Core resource group via the ``AI-Resource-Group`` header,
read from the ``AICORE_RESOURCE_GROUP`` environment variable (defaults to ``default``).
Set it if your deployment lives in a non-default resource group, or the API will reject
otherwise-valid requests.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Self

import httpx

AICORE_SERVICE_KEY_ENV = "AICORE_SERVICE_KEY"


# ===========================================================================
# Question builders — small helpers so callers don't hand-write the dicts.
# ===========================================================================
# A ``state`` payload is JSON-compatible content: a string, a structured object, or an array.
State = str | dict[str, Any] | list[Any]


def noul(instructions: State, *, true: Any = None, false: Any = None) -> dict:
    """A boolean question. The answer is P(true).

    ``true``/``false`` optionally describe what each outcome means (improves accuracy).
    """
    q: dict[str, Any] = {"type": "noul", "instructions": instructions}
    if true is not None or false is not None:
        q["criteria"] = {"true": true, "false": false}
    return q


def choice(instructions: State, options: dict[str, Any]) -> dict:
    """A single-choice question. ``options`` maps option name -> description.

    At least two options are required. Descriptions inform the answer. Note: sap-rpt-decisions can
    only predict labels it has seen, so every option here must appear as the answer in at
    least one example.
    """
    return {"type": "choice", "instructions": instructions, "criteria": options}


def score(instructions: State, levels: list[Any]) -> dict:
    """An ordered-scale question. ``levels`` is a list of level descriptions, lowest first.

    At least two levels are required. The answer is a probability-weighted score, and
    example answers use the (0-based) level index. Note: sap-rpt-decisions can only predict labels
    it has seen, so every level index must appear as the answer in at least one example.
    """
    return {"type": "score", "instructions": instructions, "criteria": levels}


# ===========================================================================
# Response types — thin wrappers over the JSON ``answers`` entries.
# ===========================================================================
@dataclass
class NoulAnswer:
    noul: float  # P(true)


@dataclass
class ChoiceAnswer:
    choice: str  # selected option
    probabilities: dict[str, float]
    confidence: float


@dataclass
class ScoreAnswer:
    score: float  # probability-weighted score
    legend: dict[str, str]  # level index -> description
    probabilities: dict[str, float]
    confidence: float


Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer


def _parse_answer(raw: dict) -> Answer:
    kind = raw["type"]
    if kind == "noul":
        return NoulAnswer(noul=raw["noul"])
    if kind == "choice":
        return ChoiceAnswer(
            choice=raw["choice"],
            probabilities=raw["probabilities"],
            confidence=raw["confidence"],
        )
    if kind == "score":
        return ScoreAnswer(
            score=raw["score"],
            legend=raw["legend"],
            probabilities=raw["probabilities"],
            confidence=raw["confidence"],
        )
    raise ValueError(f"Unknown answer type: {kind!r}")


class DecisionError(RuntimeError):
    """Raised for auth or API failures."""


# ===========================================================================
# BTP AI Core auth (client-credentials flow using AICORE_SERVICE_KEY).
# ===========================================================================
def get_token() -> str:
    """Return a BTP bearer token minted from the ``AICORE_SERVICE_KEY`` service key.

    ``AICORE_SERVICE_KEY`` must hold the AI Core service-key JSON (clientid, clientsecret,
    url). A fresh token is minted on every call; the client keeps it in memory for the
    lifetime of the session.
    """
    raw = os.environ.get(AICORE_SERVICE_KEY_ENV, "").strip()
    if not raw:
        raise DecisionError(
            f"{AICORE_SERVICE_KEY_ENV} is not set. "
            "Export the AI Core service key JSON before running."
        )
    try:
        key = json.loads(raw)  # whole service-key JSON object
    except json.JSONDecodeError:
        # Don't chain the JSONDecodeError: its .doc attribute holds the full (secret) key.
        raise DecisionError(
            f"{AICORE_SERVICE_KEY_ENV} is not valid JSON "
            "(expected the AI Core service-key object)."
        ) from None
    missing = [f for f in ("clientid", "clientsecret", "url") if not key.get(f)]
    if missing:
        raise DecisionError(
            f"{AICORE_SERVICE_KEY_ENV} is missing field(s): {', '.join(missing)}."
        )

    with httpx.Client() as client:
        resp = client.post(
            f"{key['url']}/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(key["clientid"], key["clientsecret"]),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise DecisionError(
            f"BTP token request failed (HTTP {resp.status_code}). Check {AICORE_SERVICE_KEY_ENV}."
        )
    token_data = resp.json()
    return token_data["access_token"]


# ===========================================================================
# The client.
# ===========================================================================
class RptDecisionClient:
    """Thin client for the sap-rpt-decisions model.

    Authentication is lazy: the first ``ask`` call obtains a BTP AI Core token (see
    :func:`get_token`) and keeps it in memory for reuse. If a request comes back 401
    (e.g. the token expired on a long-lived client), the token is refreshed and the request
    retried once.
    """

    def __init__(self, *, url: str, timeout: float = 120.0):
        self.url = url
        self._http = httpx.Client(timeout=timeout)
        self._token: str | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        if self._token is None or force_refresh:
            self._token = get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # BTP AI Core requires the resource-group header.
            "AI-Resource-Group": os.environ.get("AICORE_RESOURCE_GROUP", "default"),
        }

    def _post(self, payload: dict) -> dict:
        """POST ``payload`` to the Decision API, returning the parsed JSON body.

        On a 401 (e.g. the token expired), the in-memory token is cleared, a fresh
        token is minted, and the request is retried once — so a long-lived client keeps
        working across token expiry instead of replaying a stale token forever.
        """
        resp = self._http.post(self.url, headers=self._headers(), json=payload)
        if resp.status_code == 401:
            self._token = None
            resp = self._http.post(
                self.url, headers=self._headers(force_refresh=True), json=payload
            )
        if resp.status_code != 200:
            raise DecisionError(
                f"Request failed (HTTP {resp.status_code}): {resp.text}"
            )
        return resp.json()

    def ask(
        self,
        state: State,
        questions: dict[str, dict],
        examples: list[dict],
        *,
        model: str | None = None,
    ) -> dict[str, Answer]:
        """Evaluate ``state`` against ``questions``, learning from ``examples``.

        ``questions`` maps a name to a question dict (use :func:`noul`/:func:`choice`/
        :func:`score`). ``examples`` is a list of ``{"state": ..., "answers": {...}}``
        (at least two). Returns a map of question name -> parsed :class:`Answer`.
        """
        payload: dict[str, Any] = {
            "state": state,
            "questions": questions,
            "examples": examples,
        }
        if model is not None:
            payload["model"] = model  # accepted but ignored by the server

        body = self._post(payload)
        return {name: _parse_answer(raw) for name, raw in body["answers"].items()}

    def ask_raw(self, payload: dict) -> dict:
        """Send a raw request payload and return the raw JSON response."""
        return self._post(payload)
