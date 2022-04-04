from zohodb import zohodb

handler = zohodb.ZohoAuthHandler("", "")
db = zohodb.ZohoDB(handler, [
    "mydb"
])
query = db.select(table="users", criteria='"username" = "mario"')
print(query)
