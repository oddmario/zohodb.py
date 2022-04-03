import httpx
import json
import urllib.parse
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ZOHO_OAUTH_API_BASE = "https://accounts.zoho.com/oauth/v2"
ZOHO_SHEETS_API_BASE = "https://sheet.zoho.com/api/v2"
ZOHO_CLIENT_ID = ""
ZOHO_CLIENT_SECRET = ""
WORKBOOKS = []

def check_token():
    if not Path("zoho_token.json").exists():
        redirecturi = urllib.parse.quote_plus("https://example.com")
        request_code_params = [
            "response_type=code",
            f"client_id={ZOHO_CLIENT_ID}",
            "scope=ZohoSheet.dataAPI.UPDATE,ZohoSheet.dataAPI.READ",
            f"redirect_uri={redirecturi}",
            "access_type=offline",
            "prompt=consent"
        ]
        print(f"Please visit this URL: {ZOHO_OAUTH_API_BASE}/auth?" + "&".join(request_code_params))
        url = input("Paste the URL you've been redirected to here (be fast here before the code expires): ")
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
            f"client_id={ZOHO_CLIENT_ID}",
            f"client_secret={ZOHO_CLIENT_SECRET}",
            f"redirect_uri={redirecturi}",
            "grant_type=authorization_code"
        ]
        tokenreq = httpx.post(f"{ZOHO_OAUTH_API_BASE}/token?" + "&".join(request_token_params))
        with open("zoho_token.json", "w") as f:
            f.write(tokenreq.text)

def refresh_token(res):
    if "error_code" in res:
        if res['error_code'] == 2401:
            with open("zoho_token.json", "r") as f:
                refreshtoken = json.loads(f.read())['refresh_token']
            req_params = "&".join([
                f"client_id={ZOHO_CLIENT_ID}",
                f"client_secret={ZOHO_CLIENT_SECRET}",
                "grant_type=refresh_token",
                f"refresh_token={refreshtoken}"
            ])
            req = httpx.post(f"{ZOHO_OAUTH_API_BASE}/token?{req_params}")
            res = json.loads(req.text)
            token = res['access_token']
            with open("zoho_token.json", "r") as f:
                data = json.loads(f.read())
                data['access_token'] = token
                with open("zoho_token.json", "w") as fw:
                    fw.write(json.dumps(data))
            return True
    return False

def fetch_token():
    with open("zoho_token.json", "r") as f:
        data = json.loads(f.read())
        return data['access_token']
        
def store_workbook_id():
    check_token()
    workbookids = []
    req = httpx.get(f"{ZOHO_SHEETS_API_BASE}/workbooks?method=workbook.list",
    headers={
        "Authorization": f"Bearer {fetch_token()}"
    })
    res = json.loads(req.text)
    if refresh_token(res):
        return store_workbook_id()
    if res['status'] == "failure":
        raise Exception(res['error_message'])
    for workbook in res['workbooks']:
        if workbook['workbook_name'] in WORKBOOKS:
            workbookids.append(workbook['resource_id'])
    if not workbookids or workbookids == []:
        raise Exception("Unable to find a workbook with the name(s) specified")
    with open("workbookid.zohodb", "w") as f:
        f.write(json.dumps({
            "hash": hashlib.md5(str(WORKBOOKS).encode('utf-8')).hexdigest(),
            "workbooks": workbookids
        }))
    return workbookids
        
def fetch_workbook_id():
    if not Path("workbookid.zohodb").exists():
        return store_workbook_id()
    with open("workbookid.zohodb", "r") as f:
        data = f.read().strip()
        if not data or data == "":
            return store_workbook_id()
        parsed_data = json.loads(data)
        if parsed_data['hash'] != hashlib.md5(str(WORKBOOKS).encode('utf-8')).hexdigest():
            return store_workbook_id()
        return parsed_data['workbooks']
        
def zohoreq(workbook_id, data = {}):
    return httpx.post(f"{ZOHO_SHEETS_API_BASE}/{workbook_id}", data=data, headers={
        "Authorization": f"Bearer {fetch_token()}"
    })
        
def escape(criteria, parameters):
    for k, v in parameters.items():
        k = k.strip()
        v = str(v).replace("\"", "'")
        criteria = criteria.replace(k, v)
    return criteria
        
def select(table, criteria = "", columns = []):
    check_token()
    workbookids = fetch_workbook_id()
    responses = []
    returned = []
    with ThreadPoolExecutor(max_workers=50) as pool:
        responses = list(pool.map(zohoreq, workbookids, [{
            "method": "worksheet.records.fetch",
            "worksheet_name": table,
            "criteria": criteria,
            "column_names": ",".join(columns)
        }]))
    for index, res in enumerate(responses):
        res = json.loads(res.text)
        if refresh_token(res):
            return select(table, criteria, columns)
        if res['status'] == "failure":
            raise Exception(res['error_message'])
        returned.extend([dict(record, **{'workbook_id': workbookids[index]}) for record in res['records']])
    return returned
    
def insert(table, data = []):
    check_token()
    workbookids = fetch_workbook_id()
    for workbook in workbookids:
        req = zohoreq(workbook, {
            "method": "worksheet.records.add",
            "worksheet_name": table,
            "json_data": json.dumps(data)
        })
        res = json.loads(req.text)
        if refresh_token(res):
            return insert(table, data)
        if "error_code" in res:
            if res['error_code'] == 2870 or res['error_code'] == 2872:
                continue
        if res['status'] == "failure":
            raise Exception(res['error_message'])
        return True
    return False

def update(table, criteria = "", data = {}, workbook_id = ""):
    check_token()
    workbookids = fetch_workbook_id()
    for workbook in workbookids:
        if workbook_id and workbook_id != "":
            workbook = workbook_id
        req = zohoreq(workbook, {
            "method": "worksheet.records.update",
            "worksheet_name": table,
            "criteria": criteria,
            "data": json.dumps(data)
        })
        res = json.loads(req.text)
        if refresh_token(res):
            return update(table, criteria, data, workbook_id)
        if res['status'] == "failure":
            raise Exception(res['error_message'])
        if res['no_of_affected_rows'] >= 1:
            return True
        else:
            if workbook_id and workbook_id != "":
                break
            continue
    return False

def delete(table, criteria = "", row_id = 0, workbook_id = ""):
    check_token()
    if row_id > 0:
        rowid = json.dumps([row_id])
    else:
        rowid = ""
    workbookids = fetch_workbook_id()
    for workbook in workbookids:
        if workbook_id and workbook_id != "":
            workbook = workbook_id
        req = zohoreq(workbook, {
            "method": "worksheet.records.delete",
            "worksheet_name": table,
            "criteria": criteria,
            "row_array": rowid,
            "delete_rows": "true"
        })
        res = json.loads(req.text)
        if refresh_token(res):
            return delete(table, criteria, row_id, workbook_id)
        if res['status'] == "failure":
            raise Exception(res['error_message'])
        if res['no_of_rows_deleted'] >= 1:
            return True
        else:
            if workbook_id and workbook_id != "":
                break
            continue
    return False
