def response(result="succeed", msg="", info=""):
    return {
        "result": result,
        "msg": msg,
        "info": info
    }


def search_info():
    return {
        "title": "",
        "sub_title": "",
        "date": "",
        "series": "",
        "author": "",
        "genres": [],
        "description": "",
        "cover": "",
        "chapter": [],
    }


def chapter():
    return {
            "title": "",
            "url": "",
            "thumbnail": "",
            "order": 0
    }


def download_status():
    return {
            "name": "",
            "progress": "",
    }
