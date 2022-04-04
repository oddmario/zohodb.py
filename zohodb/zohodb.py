#
# ZohoDB.py
#
# @oddmario
# Mario
# mariolatif741@yandex.com
#
# License: GNU GPLv3

import httpx
import json
import urllib.parse
import hashlib
import calendar
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ZOHO_OAUTH_API_BASE = "https://accounts.zoho.com/oauth/v2"
ZOHO_SHEETS_API_BASE = "https://sheet.zoho.com/api/v2"

def ZohoWorkbookRequest(workbook_id, data):
    if not "access_token" in data:
        raise Exception("Missing the access token used for authentication")
    token = str(data['access_token']).strip()
    del data['access_token']
    try:
        return httpx.post(f"{ZOHO_SHEETS_API_BASE}/{workbook_id}", data=data, headers={
            "Authorization": f"Bearer {token}"
        })
    except Exception as e:
        raise Exception("A Zoho workbook request has failed.")

class ZohoAuthHandler:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        if not self.client_id or not self.client_secret:
            raise Exception("Missing the Zoho authentication credentials")
        self.hash = hashlib.md5((str(self.client_id) + ":" + str(self.client_secret)).encode('utf-8')).hexdigest()
        self.cache_path = f"./.zohodb/auth_cache/{self.hash}"
        Path(f"{self.cache_path}").mkdir(parents=True, exist_ok=True)
    
    def __fetch_token(self):
        redirecturi = urllib.parse.quote_plus("https://example.com")
        request_code_params = [
            "response_type=code",
            f"client_id={self.client_id}",
            "scope=ZohoSheet.dataAPI.UPDATE,ZohoSheet.dataAPI.READ",
            f"redirect_uri={redirecturi}",
            "access_type=offline",
            "prompt=consent"
        ]
        print(f"Please visit this URL: {ZOHO_OAUTH_API_BASE}/auth?" + "&".join(request_code_params))
        url = input("Paste the URL you've been redirected to after authorizing the app here (be fast here before the code expires): ")
        urlparams = url.split("/")[3].split("&")
        code = ""
        for param in urlparams:
            try:
                key = param.split("=")[0]
                val = param.split("=")[1]
                if key == 'code' or key == '?code':
                    code = val
                    break
            except Exception as e:
                continue
        request_token_params = [
            f"code={code}",
            f"client_id={self.client_id}",
            f"client_secret={self.client_secret}",
            f"redirect_uri={redirecturi}",
            "grant_type=authorization_code"
        ]
        ts = calendar.timegm(time.gmtime())
        try:
            tokenreq = httpx.post(f"{ZOHO_OAUTH_API_BASE}/token?" + "&".join(request_token_params))
        except Exception as e:
            raise Exception("Failed to request an access token")
        try:
            tokenres = json.loads(tokenreq.text)
        except Exception as e:
            raise Exception("Failed to parse the token generation response")
        if not "access_token" in tokenres:
            raise Exception("Failed to obtain an access token")
        tokenres['created_at'] = ts
        with open(f"{self.cache_path}/token.json", "w") as f:
            f.write(json.dumps(tokenres))
        return tokenres['access_token']
        
    def __refresh_token(self, refresh_token):
        req_params = "&".join([
            f"client_id={self.client_id}",
            f"client_secret={self.client_secret}",
            "grant_type=refresh_token",
            f"refresh_token={refresh_token}"
        ])
        ts = calendar.timegm(time.gmtime())
        try:
            req = httpx.post(f"{ZOHO_OAUTH_API_BASE}/token?{req_params}")
        except Exception as e:
            raise Exception("Failed to request an access token renewal")
        try:    
            res = json.loads(req.text)
        except Exception as e:
            raise Exception("Failed to parse the token renewal response")
        if not "access_token" in res:
            raise Exception("Failed to refresh the access token")
        with open(f"{self.cache_path}/token.json", "r") as f:
            data = json.loads(f.read())
            data['access_token'] = res['access_token']
            data['created_at'] = ts
            data['expires_in'] = res['expires_in']
            with open(f"{self.cache_path}/token.json", "w") as fw:
                fw.write(json.dumps(data))
        return res['access_token']
        
    def token(self):
        if not Path(f"{self.cache_path}/token.json").exists():
            with open(f"{self.cache_path}/token.json", "w") as f:
                f.write("{}")
        with open(f"{self.cache_path}/token.json", "r") as f:
            data = json.loads(f.read())
            if not "access_token" in data or not "refresh_token" in data or not "expires_in" in data or not "created_at" in data:
                return self.__fetch_token()
            if (int(data['created_at']) + int(data['expires_in'])) <= calendar.timegm(time.gmtime()):
                return self.__refresh_token(data['refresh_token'])
            return data['access_token']

class ZohoDB:
    def __init__(self, AuthHandler, workbooks, max_threads = 24):
        if not isinstance(AuthHandler, ZohoAuthHandler):
            raise Exception("Invalid ZohoAuthHandler instance passed")
        if not isinstance(workbooks, list):
            raise Exception("Invalid workbooks list passed")
        if len(workbooks) <= 0:
            raise Exception("Couldn't find any workbook names to use")
        self.AuthHandler = AuthHandler
        self.workbooks = workbooks
        self.max_threads = int(max_threads)
        self.hash = hashlib.md5(str(self.workbooks).encode('utf-8')).hexdigest()
        self.cache_path = f"./.zohodb/workbooks_cache/{self.hash}"
        Path(f"{self.cache_path}").mkdir(parents=True, exist_ok=True)
     
    def __fetch_workbooks(self):
        workbookids = []
        try:
            req = httpx.get(f"{ZOHO_SHEETS_API_BASE}/workbooks?method=workbook.list",
            headers={
                "Authorization": f"Bearer {self.AuthHandler.token()}"
            })
        except Exception as e:
            raise Exception("Failed to fetch the workbook(s) ID(s)")
        res = json.loads(req.text)
        if res['status'] == "failure":
            raise Exception(res['error_message'])
        for workbook in res['workbooks']:
            if workbook['workbook_name'] in self.workbooks:
                workbookids.append(workbook['resource_id'])
        if not workbookids or workbookids == []:
            raise Exception("Unable to find any workbooks with the name(s) specified")
        with open(f"{self.cache_path}/workbooks.json", "w") as f:
            f.write(json.dumps({
                "workbooks": workbookids
            }))
        return workbookids
        
    def workbookids(self):
        if not Path(f"{self.cache_path}/workbooks.json").exists():
            with open(f"{self.cache_path}/workbooks.json", "w") as f:
                f.write("{}")
        with open(f"{self.cache_path}/workbooks.json", "r") as f:
            data = json.loads(f.read())
            if not "workbooks" in data:
                return self.__fetch_workbooks()
            if len(data['workbooks']) <= 0:
                return self.__fetch_workbooks()
            return data['workbooks']
            
    def escape(self, criteria, parameters):
        for k, v in parameters.items():
            k = k.strip()
            v = str(v).replace("\"", "'")
            criteria = criteria.replace(k, v)
        return criteria
     
    def select(self, **kwargs):
        requireds = [
            "table",
            "criteria"
        ]
        for required in requireds:
            if not required in kwargs:
                raise Exception(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        criteria = str(kwargs['criteria'])
        if not "columns" in kwargs:
            columns = []
        else:
            columns = kwargs['columns']
        if not isinstance(columns, list):
            raise Exception("columns must be a list")
        workbookids = self.workbookids()
        responses = []
        returned = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as pool:
            responses = list(pool.map(ZohoWorkbookRequest, workbookids, [{
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.fetch",
                "worksheet_name": table,
                "criteria": criteria,
                "column_names": ",".join(columns)
            }]))
        for index, res in enumerate(responses):
            res = json.loads(res.text)
            if res['status'] == "failure":
                raise Exception(res['error_message'])
            returned.extend([dict(record, **{'workbook_id': workbookids[index]}) for record in res['records']])
        return returned
        
    def insert(self, **kwargs):
        requireds = [
            "table",
            "data"
        ]
        for required in requireds:
            if not required in kwargs:
                raise Exception(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        data = kwargs['data']
        if not isinstance(data, list):
            raise Exception("data must be a list")
        workbookids = self.workbookids()
        for workbook in workbookids:
            req = ZohoWorkbookRequest(workbook, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.add",
                "worksheet_name": table,
                "json_data": json.dumps(data)
            })
            res = json.loads(req.text)
            if "error_code" in res:
                if res['error_code'] == 2870 or res['error_code'] == 2872:
                    continue
            if res['status'] == "failure":
                raise Exception(res['error_message'])
            return True
        return False
        
    def update(self, **kwargs):
        requireds = [
            "table",
            "criteria",
            "data"
        ]
        for required in requireds:
            if not required in kwargs:
                raise Exception(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        criteria = str(kwargs['criteria'])
        data = kwargs['data']
        if not isinstance(data, dict):
            raise Exception("data must be a dictionary")
        if not "workbook_id" in kwargs:
            workbook_id = ""
        else:
            workbook_id = str(kwargs['workbook_id']).strip()
        workbookids = self.workbookids()
        return_bool = False
        for workbook in workbookids:
            if workbook_id and workbook_id != "":
                workbook = workbook_id
            req = ZohoWorkbookRequest(workbook, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.update",
                "worksheet_name": table,
                "criteria": criteria,
                "data": json.dumps(data)
            })
            res = json.loads(req.text)
            if res['status'] == "failure":
                raise Exception(res['error_message'])
            if res['no_of_affected_rows'] >= 1:
                return_bool = True
            if workbook_id and workbook_id != "":
                break
            continue
        return return_bool
        
    def delete(self, **kwargs):
        requireds = [
            "table",
            "criteria"
        ]
        for required in requireds:
            if not required in kwargs:
                raise Exception(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        criteria = str(kwargs['criteria'])
        if not "workbook_id" in kwargs:
            workbook_id = ""
        else:
            workbook_id = str(kwargs['workbook_id']).strip()
        if "row_id" in kwargs:
            row_id = int(kwargs['row_id'])
        else:
            row_id = 0
        if row_id > 0:
            rowid = json.dumps([row_id])
        else:
            rowid = ""
        workbookids = self.workbookids()
        return_bool = False
        for workbook in workbookids:
            if workbook_id and workbook_id != "":
                workbook = workbook_id
            req = ZohoWorkbookRequest(workbook, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.delete",
                "worksheet_name": table,
                "criteria": criteria,
                "row_array": rowid,
                "delete_rows": "true"
            })
            res = json.loads(req.text)
            if res['status'] == "failure":
                raise Exception(res['error_message'])
            if res['no_of_rows_deleted'] >= 1:
                return_bool = True
            if workbook_id and workbook_id != "":
                break
            continue
        return return_bool
