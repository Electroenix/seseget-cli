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


from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict
from enum import IntEnum
import json


class ResponseCode(IntEnum):
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500


@dataclass
class ApiResponse:
    """API响应基类"""

    def __init__(self,
                 code=200,
                 message="",
                 data=None):
        if data is None:
            data = {}
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_response(self):
        """返回 Flask Response，JSON 键保持原始插入顺序"""
        from flask import Response
        return Response(
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=False),
            mimetype='application/json'
        )


class SearchApiResponse:
    def __init__(self,
                 site="",
                 url="",
                 title="",
                 sub_title="",
                 date="",
                 series="",
                 author="",
                 genres=None,
                 descrip="",
                 cover="",
                 chapter=None
                 ):
        if genres is None:
            genres = []
        if chapter is None:
            chapter = []

        self.site = site
        self.url = url
        self.title = title
        self.sub_title = sub_title
        self.date = date
        self.series = series
        self.author = author
        self.genres = genres
        self.descrip = descrip
        self.cover = cover
        self.chapter = chapter

    def add_chapter(self, title="", url="", thumbnail="", order=0):
        self.chapter.append(
            {
                "title": title,
                "url": url,
                "thumbnail": thumbnail,
                "order": order
            }
        )

    def get_data(self):
        return {
            "station": self.site,
            "url": self.url,
            "title": self.title,
            "sub_title": self.sub_title,
            "date": self.date,
            "series": self.series,
            "author": self.author,
            "genres": self.genres,
            "description": self.descrip,
            "cover": self.cover,
            "chapter": self.chapter,
        }

    def to_dict(self):
        return ApiResponse(
            code=ResponseCode.SUCCESS,
            message="Success",
            data=self.get_data()
        ).to_dict()

    def to_response(self):
        return ApiResponse(
            code=ResponseCode.SUCCESS,
            message="Success",
            data=self.get_data()
        ).to_response()
