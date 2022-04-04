# ZohoDB.py
Use Zoho Sheets as a database server

## Authentication
Check https://www.zoho.com/sheet/help/api/v2/#oauthregister in order to learn the procedure of obtaining a client ID & secret. The workbooks list should contain the name(s) of your Zoho Sheets workbook(s), you can create one through the Zoho Sheets interface.

During your first ZohoDB.py query execution, you'll be asked in the console to follow a specific link so you can authorize your OAuth app, this step is done only once and the generated access token will be saved in your project directory and used for any further queries. (ZohoDB.py handles refreshing the access token whenever needed so no needa worry there)

## Usage
```py
from zohodb import zohodb

handler = zohodb.ZohoAuthHandler("my Zoho client ID here", "my Zoho client secret here")
db = zohodb.ZohoDB(handler, [
    "Spreadsheet1"
])

query = db.insert(table="users", data=[{
    "username": "Mario"
}])
```

## Criteria formatting
**NOTICE:** Any strings must be surrounded by **double quotes (`"`)**, failing to do so will throw an "invalid criteria" exception.

- `"column_name" = "value"`
  * A row in which the value of the specified column name matches the specified value

- `"column_name" contains "value"`
  * A row in which the value of the specified column name contains the specified value

- `"column_name" < x`
  * A row in which the value of the specified column name is an integer/float less than `x` (where `x` is either an integer or a float value)

- `"column_name" > x`
  * A row in which the value of the specified column name is an integer/float greater than `x` (where `x` is either an integer or a float value)

- `"column_name" = x`
  * A row in which the value of the specified column name is an integer/float equal to `x` (where `x` is either an integer or a float value)

- `"column_one" = "test" and "column_two" = "test"`
  * Specifying mandatory conditions using `and`

- `"column_one" = "test" or "column_two" = "test"`
  * Specifying optional conditions using `or`

- `("column_one" = "test" or "column_two" = "test") and "column_three" = "test"`
  * Nesting conditions using parentheses.
  * > Maximum of 5 nested criteria can be used.

## Examples usages

Assume the following table as an example spreadsheet:

| **name** | **country** | **email**           | **age** |
|----------|-------------|---------------------|---------|
| Mario    | N/A         | mario@example.com   | 19      |
| John     | US          | john@example.com    | 21      |
| Kaitlyn  | AU          | kaitlyn@example.com | 18      |

### Selecting data
```py
rows = db.select(table="Sheet1", criteria='"name" = "Mario"')
print(len(rows))
```
The output should be `1`

### Deleting data using criteria
```py
del = db.delete(table="Sheet1", criteria='"name" = "Mario"')
print(del)
```
The output should be `True`

### Deleting data using a row index
```py
row = db.select(table="Sheet1", criteria='"name" = "Mario"')[0]
del = db.delete(table="Sheet1", criteria='', row_id=row['row_index'], workbook_id=row['workbook_id'])
print(del)
```
The output should be `True`

### Updating data
```py
update = db.update(table="Sheet1", criteria='"name" = "Mario"', data={
    "name": "Mario B."
})
print(update)
```
The output should be `True`

### Inserting data
```py
insert = db.insert(table="Sheet1", data=[
    {
        "name": "User 1",
        "country": "N/A",
        "email": "user1@example.com",
        "age": 18
    },
    {
        "name": "User 2",
        "country": "N/A",
        "email": "user2@example.com",
        "age": 18
    }
])
print(update)
```
The output should be `True`

### Escaping user input
Escaping any values should be done only on the operations that take a criteria argument. `insert` for example can take any values safely since it takes JSON as its input method
```py
name_input = 'Mario" or "name" contains "a' # This is an unsafe input
safe_criteria = db.escape('"name" = ":name"', {
    ":name": name_input
})
select = db.select(table="Sheet1", criteria=safe_criteria)
```
Without escaping the above criteria (i.e. using `db.select(table="Sheet1", criteria=f'"name" = "{name_input}"')`) the final criteria would've been `"name = "Mario" or "name" contains "a"` which is an unsafe procedure.

## Zoho Sheets limitations
At the moment this file was last modified:
> Zoho Sheet supports up to 2 million cells of data in a single spreadsheet (across multiple sheets) with a maximum number of 65,536 rows and 256 columns per sheet.

ZohoDB.py allows extending this limit by creating multiple workbooks (spreadsheets) each with the same structure (*) then passing the names of all the workbooks as a list for the `workbooks` argument of `ZohoDB`. That's it, ZohoDB.py handles the rest for you :)

(*): same structure means the same sheets (tables) and the same columns structure for each sheet.

## The performance of ZohoDB.py
ZohoDB.py currently doesn't have the best performance when it comes to inserting, updating or deleting data when we have more than a single workbook (spreadsheet) used. This is expected to become more efficient in the future. However for now you can pass a `workbook_id` argument to any of `update()` or `delete()` whenever possible. This will make the query run faster since ZohoDB will know which spreadsheet has the row we're trying to update or delete.

As for `insert()` and if we have multiple workbooks, ZohoDB.py has to go through all of your workbooks to know which one can take the row(s) you're trying to insert. This also is expected to become faster in a future release :)
