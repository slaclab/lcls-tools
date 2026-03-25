"""
Client for the SLAC LCLS-II Archiver Appliance.

https://epicsarchiver.readthedocs.io/en/latest/user/userguide.html
"""

import json
import logging
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, DefaultDict, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lcls_tools.common.controls.pyepics.utils import EPICS_INVALID_VAL

logger = logging.getLogger(__name__)

ARCHIVER_URL_FORMATTER = (
    "http://lcls-archapp.slac.stanford.edu/retrieval/data/{SUFFIX}"
)

SINGLE_RESULT_SUFFIX = "getDataAtTime?at={TIME}{OFFSET}&includeProxies=true"
RANGE_RESULT_SUFFIX = "getData.json"
RANGE_MULTI_PV_SUFFIX = "getDataForPVs.json"

TIMEOUT: int = 15
DEFAULT_MAX_WORKERS: int = 4

# Legacy constant kept for backward compatability
if time.localtime().tm_isdst:
    UTC_DELTA_T = "-07:00"
else:
    UTC_DELTA_T = "-08:00"

_UNSET = object()


class ArchiverError(Exception):
    pass


class ArchiverTimeoutError(ArchiverError):
    pass


class ArchiverConnectionError(ArchiverError):
    pass


_local = threading.local()


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=4,
        pool_maxsize=8,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _get_session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = _build_session()
        _local.session = s
    return s


def _resolve_timeout(timeout):
    return TIMEOUT if timeout is _UNSET else timeout


def _get_utc_offset(dt: Optional[datetime] = None) -> str:
    """Return the Pacific time UTC offset, checking DST per timestamp."""
    if dt is None:
        dt = datetime.now()
    return "-07:00" if time.localtime(dt.timestamp()).tm_isdst else "-08:00"


def _iso_with_offset(dt: datetime, offset: str) -> str:
    return dt.isoformat(timespec="microseconds") + offset


@dataclass
class ArchiverValue:
    meta: dict = None
    secs: int = None
    val: Union[float, int, str] = None
    nanos: int = None
    severity: int = None
    status: int = None
    fields: Optional[Dict] = None
    _timestamp: Optional[datetime] = None

    def __hash__(self):
        return self.secs ^ hash(self.val) ^ self.nanos ^ self.severity ^ self.status

    @property
    def timestamp(self) -> datetime:
        if not self._timestamp:
            self._timestamp = datetime.fromtimestamp(self.secs) + timedelta(
                microseconds=self.nanos / 1000
            )
        return self._timestamp

    @property
    def is_valid(self) -> bool:
        return self.severity is not None and self.severity != EPICS_INVALID_VAL


class ArchiveDataHandler:
    def __init__(self, value_list: List[ArchiverValue] = None):
        self.value_list: List[ArchiverValue] = value_list if value_list else []

    def __str__(self):
        data = {
            "timestamps": self.timestamps,
            "values": self.values,
            "is_valid": self.validities,
        }
        return json.dumps(data, indent=4, sort_keys=True, default=str)

    def __eq__(self, other):
        if not isinstance(other, ArchiveDataHandler):
            return False
        return set(self.value_list) == set(other.value_list)

    @property
    def timestamps(self) -> List[datetime]:
        return [v.timestamp for v in self.value_list]

    @property
    def values(self) -> List[Union[str, int, float]]:
        return [v.val for v in self.value_list]

    @property
    def validities(self) -> List[bool]:
        return [v.is_valid for v in self.value_list]


def _fetch_pv_batch_range(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
    timeout: int,
    operator: Optional[str] = None,
) -> Dict[str, ArchiveDataHandler]:
    start_off = _get_utc_offset(start_time)
    end_off = _get_utc_offset(end_time)

    if operator:
        query_pvs = [f"{operator}({pv})" for pv in pv_list]
        wrapped_to_raw = {f"{operator}({pv})": pv for pv in pv_list}
    else:
        query_pvs = list(pv_list)
        wrapped_to_raw = {pv: pv for pv in pv_list}

    # getData.json silently drops all but the first PV
    suffix = RANGE_MULTI_PV_SUFFIX if len(pv_list) > 1 else RANGE_RESULT_SUFFIX
    url = ARCHIVER_URL_FORMATTER.format(SUFFIX=suffix)
    params = {
        "pv": query_pvs,
        "from": _iso_with_offset(start_time, start_off),
        "to": _iso_with_offset(end_time, end_off),
    }

    session = _get_session()
    try:
        response = session.get(url=url, timeout=timeout, params=params)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise ArchiverTimeoutError(
            f"Timeout fetching {len(pv_list)} PVs [{start_time} - {end_time}]"
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ArchiverConnectionError(
            f"Connection error fetching {len(pv_list)} PVs"
        ) from exc
    except requests.exceptions.HTTPError as exc:
        logger.error(
            "HTTP %s for %d PVs: %s",
            response.status_code, len(pv_list), response.text[:200],
        )
        raise ArchiverError(
            f"HTTP {response.status_code} fetching {len(pv_list)} PVs"
        ) from exc

    result: Dict[str, ArchiveDataHandler] = {}
    try:
        json_data = json.loads(response.text)
        for element in json_data:
            meta_name = element.get("meta", {}).get("name", "")
            raw_pv = wrapped_to_raw.get(meta_name, meta_name)
            handler = ArchiveDataHandler()
            for datum in element.get("data", []):
                handler.value_list.append(ArchiverValue(**datum))
            result[raw_pv] = handler
    except (ValueError, KeyError, IndexError) as exc:
        logger.warning("JSON parse error for %d PVs: %s", len(pv_list), exc)

    return result


def get_data_at_time(
    pv_list: List[str],
    time_requested: datetime,
    timeout=_UNSET,
) -> Dict[str, ArchiverValue]:
    timeout = _resolve_timeout(timeout)
    offset = _get_utc_offset(time_requested)
    suffix = SINGLE_RESULT_SUFFIX.format(
        TIME=time_requested.isoformat(timespec="microseconds"),
        OFFSET=offset,
    )
    url = ARCHIVER_URL_FORMATTER.format(SUFFIX=suffix)
    data = {"pv": ",".join(pv_list)}

    session = _get_session()
    try:
        response = session.post(url=url, data=data, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise ArchiverTimeoutError(
            f"Timeout in get_data_at_time for {len(pv_list)} PVs at {time_requested}"
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ArchiverConnectionError(
            "Connection error in get_data_at_time"
        ) from exc
    except requests.exceptions.HTTPError:
        logger.warning(
            "HTTP %s in get_data_at_time for %s at %s",
            response.status_code, pv_list, time_requested,
        )
        return {}

    result: Dict[str, ArchiverValue] = {}
    try:
        json_data = json.loads(response.text)
        for pv, pv_data in json_data.items():
            result[pv] = ArchiverValue(**pv_data)
    except (ValueError, KeyError) as exc:
        logger.warning(
            "JSON parse error in get_data_at_time for %s at %s: %s",
            pv_list, time_requested, exc,
        )

    return result


def get_data_with_time_interval(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
    time_delta: timedelta,
    timeout=_UNSET,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> DefaultDict[str, ArchiveDataHandler]:
    timeout = _resolve_timeout(timeout)

    sample_times: List[datetime] = []
    curr = start_time
    while curr < end_time:
        sample_times.append(curr)
        curr += time_delta

    if not sample_times:
        return defaultdict(ArchiveDataHandler)

    result: DefaultDict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)
    workers = min(max_workers, len(sample_times))
    snapshots: Dict[datetime, Dict[str, ArchiverValue]] = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_time = {
            pool.submit(get_data_at_time, pv_list, t, timeout): t
            for t in sample_times
        }
        for future in as_completed(future_to_time):
            t = future_to_time[future]
            try:
                snapshots[t] = future.result()
            except ArchiverError as exc:
                logger.warning("Failed to fetch data at %s: %s", t, exc)
                snapshots[t] = {}

    for t in sample_times:
        for pv, archiver_value in snapshots.get(t, {}).items():
            result[pv].value_list.append(archiver_value)

    return result


def get_values_over_time_range(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
    time_delta: timedelta = None,
    timeout=_UNSET,
    max_workers: int = DEFAULT_MAX_WORKERS,
    use_operator: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> DefaultDict[str, ArchiveDataHandler]:
    timeout = _resolve_timeout(timeout)

    if time_delta:
        return get_data_with_time_interval(
            pv_list, start_time, end_time, time_delta,
            timeout=timeout, max_workers=max_workers,
        )

    result: DefaultDict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)
    if not pv_list:
        return result

    try:
        batch = _fetch_pv_batch_range(
            pv_list, start_time, end_time, timeout, operator=use_operator,
        )
        result.update(batch)
    except ArchiverError as exc:
        logger.error("Batch fetch failed for %d PVs: %s", len(pv_list), exc)

    for pv in pv_list:
        if pv not in result:
            result[pv] = ArchiveDataHandler()

    if progress_callback:
        progress_callback(len(pv_list), len(pv_list))

    return result
