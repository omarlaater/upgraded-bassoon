import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning


def make_session(verify=True):
    """Build a requests session with retry/backoff for transient Bitbucket errors."""

    session = requests.Session()

    retry = Retry(
        total=4,
        read=4,
        connect=4,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"}),
    )

    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.verify = verify
    if verify is False:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    return session
