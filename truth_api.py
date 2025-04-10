from time import sleep
from typing import Any, Iterator, List, Optional
from loguru import logger
from dateutil import parser as date_parse
from datetime import datetime, timezone, date
from curl_cffi import requests
import json
import logging
import random
import os
from dotenv import load_dotenv
from structured import get_stock_market_reaction
import time

load_dotenv()  # take environment variables from .env.

logging.basicConfig(
    level=(
        logging.DEBUG
        if os.getenv("DEBUG") and os.getenv("DEBUG").lower() != "false"
        else logging.INFO
    )
)

BASE_URL = "https://truthsocial.com"
API_BASE_URL = "https://truthsocial.com/api"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 "
    "Safari/537.36"
)

# Oauth client credentials, from https://truthsocial.com/packs/js/application-d77ef3e9148ad1d0624c.js
CLIENT_ID = "9X1Fdd-pxNsAgEDNi_SfhJWi8T-vLuV2WVzKIbkTCw4"
CLIENT_SECRET = "ozF8jzI4968oTKFkEnsBC-UbLPCdrSv0MkXGQu2o_-M"

proxies = {"http": os.getenv("http_proxy"), "https": os.getenv("https_proxy")}

TRUTHSOCIAL_USERNAME = os.getenv("TRUTHSOCIAL_USERNAME")
TRUTHSOCIAL_PASSWORD = os.getenv("TRUTHSOCIAL_PASSWORD")

TRUTHSOCIAL_TOKEN = os.getenv("TRUTHSOCIAL_TOKEN")


class LoginErrorException(Exception):
    pass


class Api:
    def __init__(
        self,
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=TRUTHSOCIAL_TOKEN,
    ):
        self.ratelimit_max = 300
        self.ratelimit_remaining = None
        self.ratelimit_reset = None
        self.__username = username
        self.__password = password
        self.auth_id = token

    def __check_login(self):
        """Runs before any login-walled function to check for login credentials and generates an auth ID token"""
        if self.auth_id is None:
            if self.__username is None:
                raise LoginErrorException("Username is missing.")
            if self.__password is None:
                raise LoginErrorException("Password is missing.")
            self.auth_id = self.get_auth_id(self.__username, self.__password)
            logger.warning(f"Using token {self.auth_id}")

    def _make_session(self):
        s = requests.Session()
        return s

    def _check_ratelimit(self, resp):
        if resp.headers.get("x-ratelimit-limit") is not None:
            self.ratelimit_max = int(resp.headers.get("x-ratelimit-limit"))
        if resp.headers.get("x-ratelimit-remaining") is not None:
            self.ratelimit_remaining = int(resp.headers.get("x-ratelimit-remaining"))
        if resp.headers.get("x-ratelimit-reset") is not None:
            self.ratelimit_reset = date_parse.parse(
                resp.headers.get("x-ratelimit-reset")
            )

        if (
            self.ratelimit_remaining is not None and self.ratelimit_remaining <= 50
        ):  # We do 50 to be safe; their tracking is a bit stochastic... it can jump down quickly
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            time_to_sleep = (
                self.ratelimit_reset.replace(tzinfo=timezone.utc) - now
            ).total_seconds()
            logger.warning(
                f"Approaching rate limit; sleeping for {time_to_sleep} seconds..."
            )
            if time_to_sleep > 0:
                sleep(time_to_sleep)
            else:
                sleep(10)

    def _get(self, url: str, params: dict = None) -> Any:
        try:
            resp = self._make_session().get(
                API_BASE_URL + url,
                params=params,
                proxies=proxies,
                impersonate="chrome123",
                headers={
                    "Authorization": "Bearer " + self.auth_id,
                    "User-Agent": USER_AGENT,
                },
            )
        except Exception as e:
            logger.error(f"Curl error: {e}")

        # Will also sleep
        self._check_ratelimit(resp)

        try:
            r = resp.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON: {resp.text}")
            r = None

        return r

    def _get_paginated(self, url: str, params: dict = None, resume: str = None) -> Any:
        next_link = API_BASE_URL + url

        if resume is not None:
            next_link += f"?max_id={resume}"

        while next_link is not None:
            resp = self._make_session().get(
                next_link,
                params=params,
                proxies=proxies,
                impersonate="chrome123",
                headers={
                    "Authorization": "Bearer " + self.auth_id,
                    "User-Agent": USER_AGENT,
                },
            )
            link_header = resp.headers.get("Link", "")
            next_link = None
            for link in link_header.split(","):
                parts = link.split(";")
                if len(parts) == 2 and parts[1].strip() == 'rel="next"':
                    next_link = parts[0].strip("<>")
                    break
            logger.info(f"Next: {next_link}, resp: {resp}, headers: {resp.headers}")
            yield resp.json()

            # Will also sleep
            self._check_ratelimit(resp)

    def user_likes(
        self, post: str, include_all: bool = False, top_num: int = 40
    ) -> bool | Any:
        """Return the top_num most recent (or all) users who liked the post."""
        self.__check_login()
        top_num = int(top_num)
        if top_num < 1:
            return
        post = post.split("/")[-1]
        n_output = 0
        for followers_batch in self._get_paginated(
            f"/v1/statuses/{post}/favourited_by", resume=None, params=dict(limit=80)
        ):
            for f in followers_batch:
                yield f
                n_output += 1
                if not include_all and n_output >= top_num:
                    return

    def pull_comments(
        self,
        post: str,
        include_all: bool = False,
        only_first: bool = False,
        top_num: int = 40,
    ):
        """Return the top_num oldest (or all) replies to a post."""
        self.__check_login()
        top_num = int(top_num)
        if top_num < 1:
            return
        post = post.split("/")[-1]
        n_output = 0
        for followers_batch in self._get_paginated(
            f"/v1/statuses/{post}/context/descendants",
            resume=None,
            params=dict(sort="oldest"),
        ):
            # TO-DO: sort by sort=controversial, sort=newest, sort=oldest, sort=trending
            for f in followers_batch:
                if (only_first and f["in_reply_to_id"] == post) or not only_first:
                    yield f
                    n_output += 1
                    if not include_all and n_output >= top_num:
                        return

    def lookup(self, user_handle: str = None) -> Optional[dict]:
        """Lookup a user's information."""

        self.__check_login()
        assert user_handle is not None
        return self._get("/v1/accounts/lookup", params=dict(acct=user_handle))

    def search(
        self,
        searchtype: str = None,
        query: str = None,
        limit: int = 40,
        resolve: bool = 4,
        offset: int = 0,
        min_id: str = "0",
        max_id: str = None,
    ) -> Optional[dict]:
        """Search users, statuses or hashtags."""

        self.__check_login()
        assert query is not None and searchtype is not None

        page = 0
        while page < limit:
            if max_id is None:
                resp = self._get(
                    "/v2/search",
                    params=dict(
                        q=query,
                        resolve=resolve,
                        limit=limit,
                        type=searchtype,
                        offset=offset,
                        min_id=min_id,
                    ),
                )

            else:
                resp = self._get(
                    "/v2/search",
                    params=dict(
                        q=query,
                        resolve=resolve,
                        limit=limit,
                        type=searchtype,
                        offset=offset,
                        min_id=min_id,
                        max_id=max_id,
                    ),
                )

            offset += 40
            # added new not sure if helpful
            if not resp or all(value == [] for value in resp.values()):
                break

            yield resp

    def trending(self, limit=10):
        """Return trending truths.
        Optional arg limit<20 specifies number to return."""

        self.__check_login()
        return self._get(f"/v1/truth/trending/truths?limit={limit}")

    def group_posts(self, group_id: str, limit=20):
        self.__check_login()
        timeline = []
        posts = self._get(f"/v1/timelines/group/{group_id}?limit={limit}")
        while posts != None:
            timeline += posts
            limit = limit - len(posts)
            if limit <= 0:
                break
            max_id = posts[-1]["id"]
            posts = self._get(
                f"/v1/timelines/group/{group_id}?max_id={max_id}&limit={limit}"
            )
        return timeline

    def tags(self):
        """Return trending tags."""

        self.__check_login()
        return self._get("/v1/trends")

    def suggested(self, maximum: int = 50) -> dict:
        """Return a list of suggested users to follow."""
        self.__check_login()
        return self._get(f"/v2/suggestions?limit={maximum}")

    def trending_groups(self, limit=10):
        """Return trending group truths.
        Optional arg limit<20 specifies number to return."""

        self.__check_login()
        return self._get(f"/v1/truth/trends/groups?limit={limit}")

    def group_tags(self):
        """Return trending group tags."""

        self.__check_login()
        return self._get("/v1/groups/tags")

    def suggested_groups(self, maximum: int = 50) -> dict:
        """Return a list of suggested groups to follow."""
        self.__check_login()
        return self._get(f"/v1/truth/suggestions/groups?limit={maximum}")

    def ads(self, device: str = "desktop") -> dict:
        """Return a list of ads from Rumble's Ad Platform via Truth Social API."""

        self.__check_login()
        return self._get(f"/v3/truth/ads?device={device}")

    def user_followers(
        self,
        user_handle: str = None,
        user_id: str = None,
        maximum: int = 1000,
        resume: str = None,
    ) -> Iterator[dict]:
        assert user_handle is not None or user_id is not None
        user_id = user_id if user_id is not None else self.lookup(user_handle)["id"]

        n_output = 0
        for followers_batch in self._get_paginated(
            f"/v1/accounts/{user_id}/followers", resume=resume
        ):
            for f in followers_batch:
                yield f
                n_output += 1
                if maximum is not None and n_output >= maximum:
                    return

    def user_following(
        self,
        user_handle: str = None,
        user_id: str = None,
        maximum: int = 1000,
        resume: str = None,
    ) -> Iterator[dict]:
        assert user_handle is not None or user_id is not None
        user_id = user_id if user_id is not None else self.lookup(user_handle)["id"]

        n_output = 0
        for followers_batch in self._get_paginated(
            f"/v1/accounts/{user_id}/following", resume=resume
        ):
            for f in followers_batch:
                yield f
                n_output += 1
                if maximum is not None and n_output >= maximum:
                    return

    def pull_statuses(
        self,
        username: str,
        replies=False,
        verbose=False,
        created_after: datetime = None,
        since_id=None,
        pinned=False,
    ) -> List[dict]:
        """Pull the given user's statuses.

        Params:
            created_after : timezone aware datetime object
            since_id : number or string

        Returns a list of posts in reverse chronological order,
            or an empty list if not found.
        """

        params = {}
        user_id = self.lookup(username)["id"]
        page_counter = 0
        keep_going = True
        while keep_going:
            try:
                url = f"/v1/accounts/{user_id}/statuses"
                if pinned:
                    url += "?pinned=true&with_muted=true"
                elif not replies:
                    url += "?exclude_replies=true"
                if verbose:
                    logger.debug("--------------------------")
                    logger.debug(f"{url} {params}")
                result = self._get(url, params=params)
                page_counter += 1
            except json.JSONDecodeError as e:
                logger.error(f"Unable to pull user #{user_id}'s statuses': {e}")
                break
            except Exception as e:
                logger.error(f"Misc. error while pulling statuses for {user_id}: {e}")
                break

            if "error" in result:
                logger.error(
                    f"API returned an error while pulling user #{user_id}'s statuses: {result}"
                )
                break

            if len(result) == 0:
                break

            if not isinstance(result, list):
                logger.error(f"Result is not a list (it's a {type(result)}): {result}")

            posts = sorted(
                result, key=lambda k: k["id"], reverse=True
            )  # reverse chronological order (recent first, older last)
            params["max_id"] = posts[-1][
                "id"
            ]  # when pulling the next page, get posts before this (the oldest)

            if verbose:
                logger.debug(f"PAGE: {page_counter}")

            keep_going = False

            for post in posts:
                post["_pulled"] = datetime.now().isoformat()

                # only keep posts created after the specified date
                # exclude posts created before the specified date
                # since the page is listed in reverse chronology, we don't need any remaining posts on this page either
                post_at = date_parse.parse(post["created_at"]).replace(
                    tzinfo=timezone.utc
                )
                if (created_after and post_at <= created_after) or (
                    since_id and post["id"] <= since_id
                ):
                    keep_going = False  # stop the loop, request no more pages
                    break  # do not yeild this post or remaining (older) posts on this page

                return post

    def get_auth_id(self, username: str, password: str) -> str:
        """Logs in to Truth account and returns the session token"""
        url = BASE_URL + "/oauth/token"
        try:
            payload = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": username,
                "password": password,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "scope": "read",
            }

            sess_req = requests.request(
                "POST",
                url,
                json=payload,
                proxies=proxies,
                impersonate="chrome123",
                headers={
                    "User-Agent": USER_AGENT,
                },
            )
            print(sess_req.text)
            print(sess_req.status_code)
            sess_req.raise_for_status()
        except requests.RequestsError as e:
            logger.error(f"Failed login request: {str(e)}")
            raise SystemExit("Cannot authenticate to .")

        if not sess_req.json()["access_token"]:
            raise ValueError("Invalid truthsocial.com credentials provided!")

        return sess_req.json()["access_token"]


if __name__ == "__main__":
    now_date = datetime.now(timezone.utc)
    api = Api()
    error_sleep = 10
    while True:
        try:
            last_tweet = api.pull_statuses("realDonaldTrump", replies=False)
        except Exception as e:
            print(f"Error: {e}")
            print(f"Sleeping for {error_sleep} seconds bc of error...")
            time.sleep(10)
            error_sleep += 10
            continue
        error_sleep = 10
        if last_tweet.get("created_at") is not None:
            print(f"Last Tweet: {last_tweet['content']}")
            print(f"Created At: {last_tweet['created_at']}")
            created_at = date_parse.parse(last_tweet["created_at"]).replace(
                tzinfo=timezone.utc
            )
            if created_at > now_date:
                now_date = created_at
                print(f"Tweet: {last_tweet['content']}")
                stock_market_reaction = get_stock_market_reaction(last_tweet["content"])
                print(f"Stock Market Reaction: {stock_market_reaction}")
                if stock_market_reaction in ["extremely strong", "strong"]:
                    print("Tweet is likely to impact the stock market.")
                    # pinging the discord server
                    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                    discord_id = os.getenv("DISCORD_ID")
                    message = {
                        "content": f"<@{discord_id}>\nNew impactful tweet detected!\n\n**Tweet Content:** {last_tweet['content']}\n**Stock Market Reaction:** {stock_market_reaction}"
                    }

                    try:
                        response = requests.post(webhook_url, json=message)
                        response.raise_for_status()
                        print("Successfully sent webhook notification.")
                    except requests.RequestException as e:
                        print(f"Failed to send webhook notification: {e}")

        random_number = random.randint(10, 20)
        print(f"Sleeping for {random_number} seconds...")
        time.sleep(random_number)
