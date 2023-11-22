from report.tasks import load

def run(username, type_report, year, issn_scielo):
    load.apply_async(
        kwargs={
            "username": username, 
            "year": year, 
            "type_report": type_report,
            "issn_scielo": issn_scielo,
        }
    )
    