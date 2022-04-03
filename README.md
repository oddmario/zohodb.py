# ZohoDB.py
Use Zoho Sheets as a database server

## Configuration
First of all make sure to set the `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET` and `WORKBOOKS` variables.
Check https://www.zoho.com/sheet/help/api/v2/#oauthregister in order to learn the procedure of obtaining a client ID & secret. The workbooks list should contain the name(s) of your Zoho Sheets workbook(s), you can create one through the Zoho Sheets interface.

During your first ZohoDB.py query execution, you'll be asked in the console to follow a specific link so you can authorize your OAuth app, this step is done only once and the generated access token will be saved in your project directory and used for any further queries. (ZohoDB.py handles refreshing the access token whenever needed so no needa worry there)

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
import zohodb as db

rows = db.select("Sheet1", '"name" = "Mario"')
print(len(rows))
```
The output should be `1`

### Deleting data using criteria
```py
import zohodb as db

del = db.delete("Sheet1", '"name" = "Mario"')
print(del)
```
The output should be `True`

### Deleting data using a row index
```py
import zohodb as db

row = db.select("Sheet1", '"name" = "Mario"')[0]
del = db.delete("Sheet1", '', row['row_index'])
print(del)
```
The output should be `True`

### Updating data
```py
import zohodb as db

update = db.update("Sheet1", '"name" = "Mario"', {
    "name": "Mario B."
})
print(update)
```
The output should be `True`

### Inserting data
```py
import zohodb as db

insert = db.insert("Sheet1", [
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
Escaping any values should be done only on the operations that takes a criteria argument. `insert` for example can take any values safely since it takes JSON as its input method
```py
import zohodb as db

name_input = 'Mario" or "name" contains "a' # This is an unsafe input
safe_criteria = db.escape('"name" = ":name"', {
    ":name": name_input
})
select = db.select("Sheet1", safe_criteria)
```
Without escaping the above criteria (i.e. using `db.select("Sheet1", f'"name" = "{name_input}"')`) the final criteria would've been `"name = "Mario" or "name" contains "a"` which is an unsafe procedure.

## Zoho Sheets limitations
At the moment this file was last modified:
> Zoho Sheet supports up to 2 million cells of data in a single spreadsheet (across multiple sheets) with a maximum number of 65,536 rows and 256 columns per sheet.

ZohoDB.py allows extending this limit by creating multiple workbooks (spreadsheets) each with the same structure then adding the names of all the workbooks in the `WORKBOOKS` list of ZohoDB.py. That's it, ZohoDB.py handles the rest for you :)

## The future of ZohoDB.py
This project is currently a simple single-filed one that doesn't have any constructors, However I'm planning on turning this into a bigger project soon :)
