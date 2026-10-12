# Viva Questions and Beginner-Friendly Answers

## Big Data Analytics

### 1. What is Big Data Analytics?
It is the process of examining data to find useful patterns, summaries, or information that can support decisions.

### 2. Why is this a BDA project?
It follows a data pipeline: generation, validation, storage, analysis, and visualization. The current dataset is small, so this is a BDA learning prototype, not a distributed big-data system.

### 3. Does the project use Hadoop or Spark?
No. The current implementation uses Python, Pandas, MongoDB, Plotly, and Streamlit. Hadoop and Spark are not implemented.

### 4. What is an analytical question the project answers?
For example: how many units are pending by blood group, and how does that compare with the current group-level inventory?

### 5. Can these results predict future demand?
No. The current project reports historical patterns in synthetic records. It does not contain a forecasting model.

## Data and preprocessing

### 6. Why use synthetic data?
It avoids real donor or patient personal data and makes the demo reproducible.

### 7. How is the generated data reproducible?
The generator uses a fixed random seed. Running it with the same code produces the same generated sample.

### 8. What are the five datasets?
Blood banks, hospitals, blood inventory, donations, and hospital requests.

### 9. What does preprocessing validate?
It checks fields, identifiers, duplicates, blood groups, dates, units, and references to banks and hospitals.

### 10. What happens to an invalid record?
It is rejected from the cleaned dataset and reported with reasons. The process does not silently clip values into valid-looking data.

### 11. How many records are in the generated dataset?
There are 3 banks, 4 hospitals, 24 inventory snapshots, 500 donations, and 500 hospital requests.

### 12. Does the project contain patient records?
No. The data is generated synthetic data and does not represent real patients or donors.

## NoSQL and MongoDB

### 13. What is NoSQL?
NoSQL refers to database systems that do not require all data to be stored in traditional relational tables. MongoDB is a document database.

### 14. What is a MongoDB document?
A document is a record stored in BSON, MongoDB’s binary JSON-like format. It contains fields and values.

### 15. What is a collection?
A collection is a group of MongoDB documents, similar in broad purpose to a table, though documents can have different shapes.

### 16. What collections does this project use?
`blood_banks`, `hospitals`, `blood_inventory`, `donations`, and `hospital_requests`.

### 17. What is an index?
An index is a database structure that helps MongoDB find matching documents more efficiently. This project uses unique identifier indexes and query indexes.

### 18. What does a unique index do?
It prevents two documents from having the same indexed identifier value.

### 19. What is MongoDB aggregation?
Aggregation is a sequence of database stages that filter and transform documents, for example grouping donations by month and summing units.

### 20. What does `$setOnInsert` do in the seed process?
It sets document values only when an upsert inserts a new document. Existing documents with the same `_id` are not overwritten by that operation.

### 21. Does MongoDB enforce the hospital and bank references like a relational foreign key?
No. The application checks the bank and hospital IDs before creating or updating relevant records.

### 22. Is MongoDB Atlas configured and tested?
No. The verified environment used a local MongoDB instance. Atlas connectivity has not been verified.

### 23. What happens when MongoDB is unavailable?
The dashboard warns the user and loads cleaned CSV data in read-only mode. CRUD operations require a live MongoDB connection.

## Technology stack

### 24. What is Python used for?
Python runs the generation, validation, analytics, database-access, and dashboard logic.

### 25. What is Pandas used for?
Pandas stores tabular data in DataFrames and is used for filtering, grouping, calculating totals, and descriptive statistics.

### 26. What is PyMongo?
PyMongo is the Python driver used by this project to connect to MongoDB and perform queries, updates, deletes, and aggregations.

### 27. What does Plotly do here?
Plotly Express creates interactive charts such as bar charts and donation trend lines.

### 28. What does Streamlit do here?
Streamlit runs the Python dashboard and provides widgets, charts, tables, forms, and download controls in a web application.

## Analytics and formulas

### 29. How is pending demand calculated?
Pending units equal requested units minus supplied units. Validation requires supplied units to be between zero and requested units.

### 30. How does the project calculate overall fulfillment?
It divides total supplied units by total requested units and multiplies by 100. This is a weighted rate based on units.

### 31. Why not average the fulfillment percentages of every request?
An unweighted average treats a small request and a large request as equally important. The dashboard uses total supplied divided by total requested, as required for overall unit fulfillment.

### 32. How is potential shortage estimated?
For each blood group, it calculates the greater of pending units minus available units or zero. It then sums the positive group values.

### 33. Why calculate shortage separately by blood group?
Stock belonging to different blood groups should not be netted together as though it were interchangeable.

### 34. Is the shortage estimate a medical recommendation?
No. It is a simplified analytical estimate. It does not apply clinical compatibility, expiry, emergency priority, or transfer logistics.

### 35. How does a low-stock alert work?
The dashboard flags each selected inventory record whose available units are at or below the configurable threshold. The default threshold is 100 units.

### 36. How are donation trends grouped?
The dashboard sums donated units by calendar day, by Monday-starting week, and by calendar month.

### 37. What do mean and standard deviation tell us?
Mean is the arithmetic average. Standard deviation describes spread around the mean; the report uses sample standard deviation with `n−1`.

## Dashboard and testing

### 38. Which filters are available?
Date range, blood group, hospital, location, and blood bank. Filters apply to relevant records, such as request dates for requests and donation dates for donations.

### 39. Why does inventory use a different date field?
Inventory is a snapshot, so it uses its `last_updated` date; donations and requests use event dates.

### 40. How can analytical results be exported?
The dashboard downloads a ZIP file containing CSV summaries for selected inventory, demand, donations, shortages, alerts, and statistics.

### 41. How is the Streamlit app tested?
The tests use Streamlit’s `AppTest` to run the app script without launching a browser and check that it has no startup exception.

### 42. What other tests are included?
Tests cover data generation and preprocessing, analytics and filters, shortage and fulfillment calculations, low-stock thresholds, MongoDB repository validation using in-memory test collections, aggregation pipeline filters, and export contents.

### 43. What was the latest test result?
The latest reported test run completed with 19 tests passed. Syntax compilation with `python3 -m compileall -q src tests` also completed successfully.

### 44. Does running the tests modify the MongoDB database?
The automated CRUD tests use in-memory test collections. The latest verification did not reset, seed, or otherwise write to MongoDB.

## Sustainable Development Goals and limitations

### 45. How is the project related to SDG 3?
It provides an educational way to inspect synthetic blood availability and hospital demand. It does not measure health outcomes or provide treatment guidance.

### 46. How is the project related to SDG 10?
Its location and hospital comparisons can highlight differences for further study. Synthetic differences do not prove inequality or explain its causes.

### 47. How is the project related to SDG 17?
The database model includes both hospitals and blood banks, which supports discussion of information coordination. It does not establish a real partnership.

### 48. What is the main limitation of the dataset?
It is synthetic, small, and generated for demonstration, so the findings cannot be generalized to real blood services.

### 49. What is not included in the shortage model?
It does not model expiry, blood components, clinical compatibility, emergency priority, timing, transfer constraints, or exact local availability.

### 50. What could be improved in future?
With proper approval, a future version could use governed real data, model expiry and blood components, add secure user roles and audit trails, and evaluate forecasting separately before making predictive claims.
