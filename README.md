# What does this code do?

Both farmatodo.py and cruz_verde.py perform the same function on these websites, they retrieve all available product information. For each product, the following information is stored:

1.	INVIMA code: This code is universal for all products in Colombia, allowing for comparisons between products from different companies, even if their names vary slightly.
2.	Price.
3.	HTML: Stored in case there are inconsistencies in the information that require direct verification.

Once the product information from both websites is stored, it's processed in price_alert.py. Here: 

1. The price of products with the same INVIMA code are compared. If the price of one Farmatodo product is lower, a list is created in which the information from both, Cruz Verde and Farmatodo for the same product is stored, along with the price difference. 
2. Once all products have been compared, the resulting lists containing all products in which the price in Farmatodo is lower is stored as a csv file.  


**Once I finish uploading the repository, this code WILL NOT BE MAINTAINED.**