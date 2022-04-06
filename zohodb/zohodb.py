#
# ZohoDB.py
#
# @oddmario
# Mario
# mariolatif741@yandex.com
#
# License: GNU GPLv3

import os
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

# ----- Exception classes -----
class EmptyInput(Exception):
    """Thrown when an argument value is empty"""
    pass

class InvalidType(Exception):
    """Thrown when the wrong type/instance is used"""
    pass

class InvalidJsonResponse(Exception):
    """Thrown when an invalid/malformed JSON response is received"""
    pass

class UnexpectedResponse(Exception):
    """Thrown when the response received is missing a key we want"""
    pass

class HttpRequestError(Exception):
    """Thrown on the occurence of a HttpX request error"""
    pass

class MissingData(Exception):
    """Thrown when a requirement is missing"""
    pass

class InvalidCacheTable(Exception):
    """Thrown when the specified cache table doesn't exist"""
    pass

class CorruptedCacheTable(Exception):
    """Thrown when a cache table contains malformed JSON data"""
    pass
# ----------

def ZohoWorkbookRequest(workbook_id, data):
    if not "access_token" in data:
        raise MissingData("Missing the access token used for authentication")
    token = str(data['access_token']).strip()
    del data['access_token']
    try:
        return httpx.post(f"{ZOHO_SHEETS_API_BASE}/{workbook_id}", data=data, headers={
            "Authorization": f"Bearer {token}"
        })
    except httpx.RequestError as e:
        raise HttpRequestError(f"A Zoho workbook request has failed: {e}")
        
class ZohoDBCache:
    def __init__(self, hash):
        if not hash:
            raise MissingData("The cache hash is required")
        self.hash = hash
        self.cache_path = f"./.zohodb/db_cache/{self.hash}"
        Path(f"{self.cache_path}").mkdir(parents=True, exist_ok=True)
        
    def __wait_till_released(self, table):
        while True:
            if Path(f"{self.cache_path}/{table}.lock").exists():
                time.sleep(1)
                continue
            else:
                break
        return True
        
    def __lock(self, table):
        open(f"{self.cache_path}/{table}.lock", 'a').close()
        return True
        
    def __release(self, table):
        if Path(f"{self.cache_path}/{table}.lock").exists():
            os.remove(f"{self.cache_path}/{table}.lock")
        return True
            
    def __release_and_return(self, return_value, table):
        self.__release(table)
        return return_value

    def set(self, table, key, value):
        self.__wait_till_released(table)
        self.__lock(table)
        if not Path(f"{self.cache_path}/{table}.json").exists():
            with open(f"{self.cache_path}/{table}.json", "w") as f:
                data = {}
                data[key] = value
                f.write(json.dumps(data))
                return self.__release_and_return(True, table)
        with open(f"{self.cache_path}/{table}.json", "r") as f:
            try:
                data = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                self.__release(table)
                raise CorruptedCacheTable
            data[key] = value
            with open(f"{self.cache_path}/{table}.json", "w") as fw:
                fw.write(json.dumps(data))
                return self.__release_and_return(True, table)
        return self.__release_and_return(False, table)
                
    def get(self, table, key):
        if not Path(f"{self.cache_path}/{table}.json").exists():
            raise InvalidCacheTable
        with open(f"{self.cache_path}/{table}.json", "r") as f:
            try:
                data = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                raise CorruptedCacheTable
            if key in data:
                return data[key]
            else:
                return None
                
    def delete(self, table, key):
        if not Path(f"{self.cache_path}/{table}.json").exists():
            raise InvalidCacheTable
        self.__wait_till_released(table)
        self.__lock(table)
        with open(f"{self.cache_path}/{table}.json", "r") as f:
            try:
                data = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                self.__release(table)
                raise CorruptedCacheTable
            if key in data:
                del data[key]
            else:
                return self.__release_and_return(False, table)
            with open(f"{self.cache_path}/{table}.json", "w") as fw:
                fw.write(json.dumps(data))
                return self.__release_and_return(True, table)
        return self.__release_and_return(False, table)

class ZohoAuthHandler:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        if not self.client_id or not self.client_secret:
            raise MissingData("Missing the Zoho authentication credentials")
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
            except IndexError:
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
        except httpx.RequestError as e:
            raise HttpRequestError(f"Failed to request an access token: {e}")
        try:
            tokenres = json.loads(tokenreq.text)
        except json.decoder.JSONDecodeError as e:
            raise InvalidJsonResponse(f"Failed to parse the token generation response: {e}")
        if not "access_token" in tokenres:
            raise UnexpectedResponse("Failed to obtain an access token")
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
        except httpx.RequestError as e:
            raise HttpRequestError(f"Failed to request an access token renewal: {e}")
        try:    
            res = json.loads(req.text)
        except json.decoder.JSONDecodeError as e:
            raise InvalidJsonResponse(f"Failed to parse the token renewal response: {e}")
        if not "access_token" in res:
            raise UnexpectedResponse("Failed to refresh the access token")
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
            raise InvalidType("Invalid ZohoAuthHandler instance passed")
        if not isinstance(workbooks, list):
            raise InvalidJsonResponse("Invalid workbooks list passed")
        if len(workbooks) <= 0:
            raise EmptyInput("Couldn't find any workbook names to use")
        self.AuthHandler = AuthHandler
        self.workbooks = workbooks
        self.max_threads = int(max_threads)
        self.hash = hashlib.md5(str(self.workbooks).encode('utf-8')).hexdigest()
        self.cache = ZohoDBCache(self.hash)

    def __fetch_workbooks(self):
        workbookids = []
        try:
            req = httpx.get(f"{ZOHO_SHEETS_API_BASE}/workbooks?method=workbook.list",
            headers={
                "Authorization": f"Bearer {self.AuthHandler.token()}"
            })
        except httpx.RequestError as e:
            raise HttpRequestError(f"Failed to fetch the workbook(s) ID(s): {e}")
        res = json.loads(req.text)
        if res['status'] == "failure":
            raise UnexpectedResponse(res['error_message'])
        for workbook in res['workbooks']:
            if workbook['workbook_name'] in self.workbooks:
                workbookids.append(workbook['resource_id'])
        if not workbookids or workbookids == []:
            raise UnexpectedResponse("Unable to find any workbooks with the name(s) specified")
        self.cache.set("workbooks", "workbooks", workbookids)
        return workbookids
        
    def workbookids(self):
        try:
            wbs = self.cache.get("workbooks", "workbooks")
        except InvalidCacheTable:
            return self.__fetch_workbooks()
        if wbs == None or len(wbs) <= 0:
            return self.__fetch_workbooks()
        return wbs
            
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
                raise MissingData(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        criteria = str(kwargs['criteria'])
        if not "columns" in kwargs:
            columns = []
        else:
            columns = kwargs['columns']
        if not isinstance(columns, list):
            raise InvalidType("columns must be a list")
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
                raise UnexpectedResponse(res['error_message'])
            returned.extend([dict(record, **{'workbook_id': workbookids[index]}) for record in res['records']])
        return returned
        
    def insert(self, **kwargs):
        requireds = [
            "table",
            "data"
        ]
        for required in requireds:
            if not required in kwargs:
                raise MissingData(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        data = kwargs['data']
        if not isinstance(data, list):
            raise InvalidType("data must be a list")
        workbookids = self.workbookids()
        for workbook in workbookids:
            try:
                cached_ts = self.cache.get("full_workbooks", str(workbook))
                if cached_ts != None:
                    if (cached_ts + 3600) <= calendar.timegm(time.gmtime()):
                        self.cache.delete("full_workbooks", str(workbook))
                    else:
                        break
            except InvalidCacheTable:
                pass
            req = ZohoWorkbookRequest(workbook, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.add",
                "worksheet_name": table,
                "json_data": json.dumps(data)
            })
            res = json.loads(req.text)
            if "error_code" in res:
                if res['error_code'] == 2870 or res['error_code'] == 2872:
                    self.cache.set("full_workbooks", str(workbook), calendar.timegm(time.gmtime()))
                    continue
            if res['status'] == "failure":
                raise UnexpectedResponse(res['error_message'])
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
                raise MissingData(f"Missing the required argument '{required}'")
        table = str(kwargs['table'])
        criteria = str(kwargs['criteria'])
        data = kwargs['data']
        if not isinstance(data, dict):
            raise InvalidType("data must be a dictionary")
        if not "workbook_id" in kwargs:
            workbook_id = ""
        else:
            workbook_id = str(kwargs['workbook_id']).strip()
        return_bool = False
        if workbook_id and workbook_id != "":
            req = ZohoWorkbookRequest(workbook_id, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.update",
                "worksheet_name": table,
                "criteria": criteria,
                "data": json.dumps(data)
            })
            res = json.loads(req.text)
            if res['status'] == "failure":
                raise UnexpectedResponse(res['error_message'])
            if res['no_of_affected_rows'] >= 1:
                return_bool = True
        else:
            responses = []
            workbookids = self.workbookids()
            with ThreadPoolExecutor(max_workers=self.max_threads) as pool:
                responses = list(pool.map(ZohoWorkbookRequest, workbookids, [{
                    "access_token": self.AuthHandler.token(),
                    "method": "worksheet.records.update",
                    "worksheet_name": table,
                    "criteria": criteria,
                    "data": json.dumps(data)
                }]))
            for res in responses:
                res = json.loads(res.text)
                if res['status'] == "failure":
                    raise UnexpectedResponse(res['error_message'])
                if res['no_of_affected_rows'] >= 1:
                    return_bool = True
        return return_bool
        
    def delete(self, **kwargs):
        requireds = [
            "table",
            "criteria"
        ]
        for required in requireds:
            if not required in kwargs:
                raise MissingData(f"Missing the required argument '{required}'")
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
        return_bool = False
        affected_workbooks = []
        if workbook_id and workbook_id != "":
            req = ZohoWorkbookRequest(workbook_id, {
                "access_token": self.AuthHandler.token(),
                "method": "worksheet.records.delete",
                "worksheet_name": table,
                "criteria": criteria,
                "row_array": rowid,
                "delete_rows": "true"
            })
            res = json.loads(req.text)
            if res['status'] == "failure":
                raise UnexpectedResponse(res['error_message'])
            if res['no_of_rows_deleted'] >= 1:
                if not workbook_id in affected_workbooks:
                    affected_workbooks.append(workbook_id)
                return_bool = True
        else:
            responses = []
            workbookids = self.workbookids()
            with ThreadPoolExecutor(max_workers=self.max_threads) as pool:
                responses = list(pool.map(ZohoWorkbookRequest, workbookids, [{
                    "access_token": self.AuthHandler.token(),
                    "method": "worksheet.records.delete",
                    "worksheet_name": table,
                    "criteria": criteria,
                    "row_array": rowid,
                    "delete_rows": "true"
                }]))
            for index, res in enumerate(responses):
                res = json.loads(res.text)
                if res['status'] == "failure":
                    raise UnexpectedResponse(res['error_message'])
                if res['no_of_rows_deleted'] >= 1:
                    if not workbookids[index] in affected_workbooks:
                        affected_workbooks.append(workbookids[index])
                    return_bool = True
        if return_bool == True:
            for workbook in affected_workbooks:
                try:
                    self.cache.delete("full_workbooks", str(workbook))
                except InvalidCacheTable:
                    pass
        return return_bool
