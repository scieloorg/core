from article.tasks import load_preprint


def run(user_id=None, oai_pmh_preprint_uri=None):
	oai_pmh_preprint_uri = oai_pmh_preprint_uri or "https://preprints.scielo.org/index.php/scielo/oai"
    load_preprint.apply_async(args=(user_id, oai_pmh_preprint_uri))
