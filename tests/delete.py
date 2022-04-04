from zohodb import zohodb

handler = zohodb.ZohoAuthHandler("", "")
db = zohodb.ZohoDB(handler, [
    "mydb"
])
query = db.delete(table="users", criteria='"username" = "kaitlyn"')
print(query) # expected: True
