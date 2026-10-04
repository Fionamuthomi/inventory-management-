"""Mock database seed data.

Fields mirror what the OpenFoodFacts `product` object contains
(product_name, brands, ingredients_text, ...), plus store-specific fields
(id, price, stock).
"""

SEED_ITEMS = [
    {
        "id": 1, "barcode": "5449000000996", "product_name": "Coca-Cola",
        "brands": "Coca-Cola", "categories": "Beverages, Sodas",
        "ingredients_text": "Carbonated water, sugar, colour (caramel E150d), phosphoric acid, natural flavourings including caffeine",
        "nutriscore_grade": "e", "image_url": None, "price": 1.50, "stock": 120,
    },
    {
        "id": 2, "barcode": "3017620422003", "product_name": "Nutella",
        "brands": "Ferrero", "categories": "Spreads, Hazelnut spreads",
        "ingredients_text": "Sugar, palm oil, hazelnuts 13%, skimmed milk powder 8.7%, fat-reduced cocoa 7.4%, emulsifier: lecithins (soya), vanillin",
        "nutriscore_grade": "e", "image_url": None, "price": 4.99, "stock": 45,
    },
    {
        "id": 3, "barcode": "0025293000926", "product_name": "Organic Almond Milk",
        "brands": "Silk", "categories": "Plant-based milks, Almond milks",
        "ingredients_text": "Filtered water, almonds, cane sugar, sea salt, locust bean gum, sunflower lecithin, gellan gum",
        "nutriscore_grade": "b", "image_url": None, "price": 3.49, "stock": 8,
    },
    {
        "id": 4, "barcode": "8076800195057", "product_name": "Penne Rigate",
        "brands": "Barilla", "categories": "Pasta, Dried pastas",
        "ingredients_text": "Durum wheat semolina, water",
        "nutriscore_grade": "a", "image_url": None, "price": 1.99, "stock": 200,
    },
    {
        "id": 5, "barcode": "5000159407236", "product_name": "Milk Chocolate Bar",
        "brands": "Cadbury", "categories": "Snacks, Chocolates",
        "ingredients_text": "Milk, sugar, cocoa butter, cocoa mass, vegetable fats, emulsifiers (E442, E476), flavourings",
        "nutriscore_grade": "e", "image_url": None, "price": 1.25, "stock": 3,
    },
    {
        "id": 6, "barcode": "5000112637922", "product_name": "Orange Juice",
        "brands": "Tropicana", "categories": "Beverages, Fruit juices",
        "ingredients_text": "Orange juice from concentrate",
        "nutriscore_grade": "c", "image_url": None, "price": 2.79, "stock": 60,
    },
]
