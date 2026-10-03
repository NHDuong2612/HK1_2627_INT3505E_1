from flask import request, jsonify
import uuid

ERROR_BASE = "https://api.example.com/probs"

class ApiProblem(Exception):
    def __init__(self, status_code, title, detail=None, type_path=None, **extra):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = f"{ERROR_BASE}/{type_path}" if type_path else "about:blank"
        self.extra = extra
    """
    def to_dict(self):
        return {
            "type": self.type,
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail
        }
    """
    @staticmethod
    def _problem(status, title, detail=None, type_part=None, **extra):
        body ={
            "type": f"{ERROR_BASE}/{type_part}" if type_part else "about:blank",
            "title": title,
            "status": status,
            "instance": request.path,
            "trace_id": str(uuid.uuid4()),
        }
        if detail:
            body["detail"] = detail
        body.update(extra)

        resp = jsonify(body)
        resp.status_code = status
        resp.headers["Content-Type"] = "application/problem+json"
        return resp
    
