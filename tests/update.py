from zohodb import zohodb

handler = zohodb.ZohoAuthHandler("", "")
db = zohodb.ZohoDB(handler, [
    "mydb"
])
query = db.update(table="users", criteria='"username" = "kaitlyn"', data={
    "email": "user@example.com"
})
print(query) # expected: True
