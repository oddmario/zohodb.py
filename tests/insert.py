from zohodb import zohodb

handler = zohodb.ZohoAuthHandler("", "")
db = zohodb.ZohoDB(handler, [
    "mydb"
])
query = db.insert(table="users", data=[{
    "username": "kaitlyn"
}])
print(query) # expected: True
