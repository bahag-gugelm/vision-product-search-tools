import logging
from datetime import datetime
from urllib.parse import urljoin

from pyrfc6266 import requests_response_to_filename

from requests import Session, adapters
from requests.auth import HTTPBasicAuth


class BahagAssetsAPI:
    def __init__(self, user: str, password: str, base_url: str):
        self.access_token = None
        self.token_issued_at = datetime.fromtimestamp(0)
        self.token_expires_in = 0
        self.auth = HTTPBasicAuth(user, password)
        self.session = Session()
        self.auth_url = urljoin(base_url, "/oauth2/accesstoken")
        self.api_url = urljoin(base_url, "/v1/assets-masterdata/")
        self.logger = logging.getLogger(__name__)
        self.adapter = adapters.HTTPAdapter(
            pool_connections=32,
            pool_maxsize=64
            )
        self.session.mount('http://', self.adapter)
        self.session.mount('https://', self.adapter)
        

    def __enter__(self):
        self.auth_session()
        return self

    def __exit__(self, type, value, traceback):
        self.session.close()

    # noinspection PyDefaultArgument
    def auth_session(
        self, data: dict = {"grant_type": "client_credentials"}
    ):
        """Open a session"""
        r = self.session.post(
            url=self.auth_url, auth=self.auth, data=data
        )
        r_json = r.json()
        self.access_token = r_json.get("access_token")
        if not self.access_token:
            raise Exception("Unable to get auth token, check the credentials.")

        self.logger.info(f"Authenticated to {self.auth_url} successfully")
        self.token_issued_at = datetime.fromtimestamp(
            int(r_json["issued_at"]) / 1e3
        )
        self.token_expires_in = int(r_json["expires_in"])
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    @property
    def token_lifetime(self):
        return (
            self.token_expires_in
            - (datetime.now() - self.token_issued_at).seconds
        )

    def get_assets_data(
        self,
        bahag_id: str,
        country_code: str = "de",
        language_id: str = "de-DE"
        ):
        try:
            if not self.access_token:
                raise Exception(
                    "Client instance is not authenticated. "
                    "Use context manager 'with' statement or "
                    "call 'self.auth_session()' explicitly"
                )

            if not self.token_lifetime >= 5:
                self.auth_session()
            q_url = urljoin(
                self.api_url,
                f"2/{country_code}/assets/articlenumbers/{bahag_id}?language_id={language_id}"
                )
            r = self.session.get(url=q_url)
            if r.ok:
                return r.json()
            self.logger.warning(f"Can't get API data, id={bahag_id}, status: {r.status_code}")
        except Exception as e:
            self.logger.exception(e)
            raise e
    
    def get_asset_file(self, url: str):
        r = self.session.get(url=url, stream=True)
        filename = requests_response_to_filename(r)
        filesize = r.headers["Content-length"]
        if r.ok:
            return (filename, int(filesize), r.content)
        self.logger.warning(f"Can't get remote file because of {r.status_code}")
