import json
import logging
import os

from django.db.utils import DataError

from altmetric import models


def load(file_path, file, user):
    """
    Create the record of a Altmetric.
    'jdata' object is a dict content the data to create each Altmetric records.
    Something like this:
        {
            "query": {
            "total": 1,
            "articles": 1360,
            "page": 0,
            "num_results": 25,
            "ms": 110
        },
        "results": [...]
            }
    """
    try:
        logging.info("json_read: %s/%s" % (file_path, file))
        json_read = open(os.path.join(file_path, file), "r").read()
    except Exception as e:
        logging.info(e)

    if json_read:
        try:
            jdata = json.loads(json_read)
            issn_scielo = jdata.get("issn_scielo")

            logging.info("issn_scielo %s in process", issn_scielo)
            if issn_scielo:
                rawaltmetric = models.RawAltmetric.objects.filter(
                    issn_scielo=issn_scielo
                )
                if len(rawaltmetric) == 0:
                    rawaltmetric = models.RawAltmetric()
                    rawaltmetric.issn_scielo = issn_scielo
                    rawaltmetric.extraction_date = jdata.get("extraction_date")
                    rawaltmetric.resource_type = "journal"
                else:
                    logging.info("json_data %s will be updated", file)
                    rawaltmetric = rawaltmetric[0]
                    rawaltmetric.extraction_date = jdata.get("extraction_date")

                rawaltmetric.json = jdata

                try:
                    logging.info("json_data %s will be saved", file)
                    rawaltmetric.save()
                except Exception as e:
                    logging.info(e)

        except Exception as e:
            logging.info(e)
