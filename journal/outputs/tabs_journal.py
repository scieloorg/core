
def get_issn_scielo(obj, dict_data={}):
    try:
        dict_data["ISSN SciELO"] = obj.issn_scielo
    except AttributeError as e:
        print(f"There is no information about 'issn_scielo' in the object {obj}")


