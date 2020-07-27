from logging import ERROR, Handler, getLogger

import ujson as json
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionTimeout


class ESHandler(Handler):
    def __init__(self, es, index):
        super().__init__()
        self.es = Elasticsearch(es)
        self.index = index
        getLogger("elasticsearch").setLevel(ERROR)
        getLogger("elasticsearch.trace").setLevel(ERROR)
        getLogger("urllib3").setLevel(ERROR)

    def emit(self, record):
        if isinstance(record.msg, dict):
            record.msg = json.dumps(record.msg)

        log_entry = self.format(record)

        # Push action to ES
        try:
            return self.es.index(
                index=self.index, doc_type="python_log", body=log_entry
            )
        except ConnectionTimeout:
            return False
