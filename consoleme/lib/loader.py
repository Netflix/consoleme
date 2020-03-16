import json
import os

import time

from consoleme.exceptions.exceptions import (
    WebpackError,
    WebpackLoaderBadStatsError,
    WebpackLoaderTimeoutError,
    WebpackBundleLookupError,
)

settings = {}

# TODO, move followings into config yaml file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_STATS = "webpack-stats.dev.json"
PROD_STATS = "webpack-stats.prod.json"
BUNDLE_DIR_NAME = "bundles/"


class WebpackLoader(object):
    _assets = {}

    def __init__(self, name, config):
        self.name = name
        self.config = config

    def load_assets(self):
        # TODO, get stats file path from config
        # TODO, select stats file based on development or production
        try:
            ENV_STAT_FILE = DEV_STATS if self.config.get("development") else PROD_STATS
            STATS_FILE = os.path.join(BASE_DIR, ENV_STAT_FILE)
            with open(STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except IOError:
            raise IOError(
                "Error reading {0}. Are you sure webpack has generated "
                "the file and the path is correct?".format(STATS_FILE)
            )

    def get_assets(self):
        # TODO, get assets from CACHE
        return self.load_assets()

    def filter_chunks(self, chunks):
        for chunk in chunks:
            chunk["url"] = self.get_chunk_url(chunk)
            yield chunk

    def get_chunk_url(self, chunk):
        public_path = chunk.get("publicPath")
        if public_path:
            return public_path

        relpath = "{0}{1}".format(BUNDLE_DIR_NAME, chunk["name"])
        # TODO: revisit this
        # return staticfiles_storage.url(relpath)
        return relpath

    def get_bundle(self, bundle_name):
        assets = self.get_assets()

        # poll when debugging and block request until bundle is compiled
        # or the build times out
        if self.config.get("development"):
            timeout = 0
            timed_out = False
            start = time.time()
            while assets["status"] == "compiling" and not timed_out:
                time.sleep(0.1)
                if timeout and (time.time() - timeout > start):
                    timed_out = True
                assets = self.get_assets()

            if timed_out:
                raise WebpackLoaderTimeoutError(
                    "Timed Out. Bundle took more than {1} seconds "
                    "to compile.".format(timeout)
                )

        if assets.get("status") == "done":
            chunks = assets["chunks"].get(bundle_name, None)
            if chunks is None:
                raise WebpackBundleLookupError(
                    "Cannot resolve bundle {0}.".format(bundle_name)
                )
            return self.filter_chunks(chunks)

        elif assets.get("status") == "error":
            if "file" not in assets:
                assets["file"] = ""
            if "error" not in assets:
                assets["error"] = "Unknown Error"
            if "message" not in assets:
                assets["message"] = ""
            error = u"""
            {error} in {file}
            {message}
            """.format(
                **assets
            )
            raise WebpackError(error)

        raise WebpackLoaderBadStatsError(
            "The stats file does not contain valid data. Make sure "
            "webpack-bundle-tracker plugin is enabled and try to run "
            "webpack again."
        )
