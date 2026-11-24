# gen-product-catalog

Source file: gen-product-catalog.json
Source type: JSON

## gen-product-catalog

```json
{
  "catalog": {
    "supplier": "Brightwater Provisions, Inc.",
    "generated": "2028-02-01T06:30:00Z",
    "currency": "USD",
    "product_count": 8,
    "schema": "catalog export 2.1",
    "price_list": "Foodservice 2028 Q1"
  },
  "products": [
    {
      "sku": "FZ-SAL-0412",
      "name": "Atlantic salmon fillets, skin on",
      "category": "Frozen seafood",
      "pack": {
        "units": 10,
        "unit_size": "2 lb",
        "case_weight_lb": 21.5
      },
      "pricing": {
        "list": 189.9,
        "tiers": [
          {
            "min_cases": 10,
            "price": 182.4
          },
          {
            "min_cases": 40,
            "price": 176.25
          }
        ]
      },
      "storage": "frozen",
      "allergens": [
        "fish"
      ],
      "origin": {
        "country": "Norway",
        "plant": "Ålesund"
      },
      "discontinued": false,
      "replaced_by": null
    },
    {
      "sku": "DY-MLK-1001",
      "name": "Whole milk, half gallon",
      "category": "Dairy",
      "pack": {
        "units": 9,
        "unit_size": "64 fl oz",
        "case_weight_lb": 40.2
      },
      "pricing": {
        "list": 27.15,
        "tiers": []
      },
      "storage": "refrigerated",
      "allergens": [
        "milk"
      ],
      "origin": {
        "country": "USA",
        "plant": "Plant City"
      },
      "discontinued": false,
      "replaced_by": null,
      "shelf_life_days": 18
    },
    {
      "sku": "BK-BRD-0207",
      "name": "Brioche burger buns, 4 inch",
      "category": "Bakery",
      "pack": {
        "units": 72,
        "unit_size": "3 oz",
        "case_weight_lb": 14.0
      },
      "pricing": {
        "list": 38.6,
        "tiers": [
          {
            "min_cases": 25,
            "price": 36.9
          }
        ]
      },
      "storage": "frozen",
      "allergens": [
        "wheat",
        "milk",
        "egg"
      ],
      "origin": {
        "country": "USA",
        "plant": "Atlanta"
      },
      "discontinued": true,
      "replaced_by": "BK-BRD-0219",
      "notes": "Recall lot 27-311 closed; ships in 12\" sleeves"
    },
    {
      "sku": "PR-AVO-0050",
      "name": "Hass avocados, size 48",
      "category": "Fresh produce",
      "pack": {
        "units": 48,
        "unit_size": "each",
        "case_weight_lb": 25.0
      },
      "pricing": {
        "list": 61.75,
        "tiers": [
          {
            "min_cases": 20,
            "price": 58.5
          }
        ]
      },
      "storage": "ambient until ripe",
      "allergens": [],
      "origin": {
        "country": "Mexico",
        "plant": "Uruapan, Michoacán"
      },
      "discontinued": false,
      "replaced_by": null,
      "seasonal": true
    },
    {
      "sku": "DG-OIL-0330",
      "name": "Canola frying oil, jug",
      "category": "Dry grocery",
      "pack": {
        "units": 1,
        "unit_size": "35 lb",
        "case_weight_lb": 36.1
      },
      "pricing": {
        "list": 44.2,
        "tiers": [
          {
            "min_cases": 50,
            "price": 41.05
          },
          {
            "min_cases": 200,
            "price": 39.8
          }
        ]
      },
      "storage": "ambient",
      "allergens": [],
      "origin": {
        "country": "Canada",
        "plant": "Saskatoon"
      },
      "discontinued": false,
      "replaced_by": null
    },
    {
      "sku": "FZ-SHR-0921",
      "name": "White shrimp 16/20, peeled and deveined",
      "category": "Frozen seafood",
      "pack": {
        "units": 5,
        "unit_size": "2 lb",
        "case_weight_lb": 10.8
      },
      "pricing": {
        "list": 112.0,
        "tiers": [
          {
            "min_cases": 15,
            "price": 107.35
          }
        ]
      },
      "storage": "frozen",
      "allergens": [
        "shellfish"
      ],
      "origin": {
        "country": "Ecuador",
        "plant": "Guayaquil"
      },
      "discontinued": false,
      "replaced_by": null,
      "certifications": [
        "BAP 2-star",
        "ASC"
      ]
    },
    {
      "sku": "DY-CHS-0415",
      "name": "Queso fresco, \"Doña Rosa\" brand",
      "category": "Dairy",
      "pack": {
        "units": 12,
        "unit_size": "10 oz",
        "case_weight_lb": 8.3
      },
      "pricing": {
        "list": 46.8,
        "tiers": []
      },
      "storage": "refrigerated",
      "allergens": [
        "milk"
      ],
      "origin": {
        "country": "USA",
        "plant": "Hialeah"
      },
      "discontinued": false,
      "replaced_by": null,
      "shelf_life_days": 45
    },
    {
      "sku": "PR-LET-0120",
      "name": "Romaine hearts, 3 count",
      "category": "Fresh produce",
      "pack": {
        "units": 12,
        "unit_size": "3 ct bag",
        "case_weight_lb": 18.4
      },
      "pricing": {
        "list": 33.25,
        "tiers": [
          {
            "min_cases": 30,
            "price": 31.6
          }
        ]
      },
      "storage": "refrigerated",
      "allergens": [],
      "origin": {
        "country": "USA",
        "plant": "Salinas"
      },
      "discontinued": false,
      "replaced_by": null,
      "seasonal": true
    }
  ]
}
```
