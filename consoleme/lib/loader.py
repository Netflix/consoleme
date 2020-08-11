import json
import os
import time

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    WebpackBundleLookupError,
    WebpackError,
    WebpackLoaderBadStatsError,
    WebpackLoaderTimeoutError,
)

settings = {}

BASE_DIR = config.get(
    "webpack.loader.base_directory",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
DEV_STATS = config.get("webpack.loader.dev_stats", "webpack-stats.dev.json")
PROD_STATS = config.get("webpack.loader.prod_stats", "webpack-stats.prod.json")
BUNDLE_DIR_NAME = config.get("webpack.loader.bundle_dir", "bundles/")


class WebpackLoader(object):
    _assets = {}

    def __init__(self, name, config):
        self.name = name
        self.config = config

    def load_assets(self):
        # TODO, get stats file path from config
        # TODO, select stats file based on development or production
        ENV_STAT_FILE = DEV_STATS if self.config.get("development") else PROD_STATS
        STATS_FILE = os.path.join(BASE_DIR, ENV_STAT_FILE)
        try:
            with open(STATS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except IOError:
            raise IOError(
                f"Error reading {STATS_FILE}. Are you sure webpack has generated "
                "the file and the path is correct?"
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
                    f"Timed Out. Bundle took more than {timeout} seconds " "to compile."
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
            error = "{} in {} {}".format(
                assets["error"], assets["file"], assets["message"]
            )
            raise WebpackError(error)

        raise WebpackLoaderBadStatsError(
            "The stats file does not contain valid data. Make sure "
            "webpack-bundle-tracker plugin is enabled and try to run "
            "webpack again."
        )
