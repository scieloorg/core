from report.tasks import report_csv_generator

def run(username, type_report, year, issn_scielo):
    report_csv_generator.apply_async(
        kwargs={
            "username": username, 
            "issn_scielo": issn_scielo,
            "type_report": type_report,
            "year": year, 
        }
    )
    