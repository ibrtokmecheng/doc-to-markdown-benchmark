# gen-api-response

Source file: gen-api-response.json
Source type: JSON

## gen-api-response

```json
{
  "object": "list",
  "url": "/v2/customers",
  "api_version": "2026-10-01",
  "request_id": "req_7Hq2LmX9a4Kd",
  "generated_at": "2026-11-20T14:05:12Z",
  "pagination": {
    "page": 2,
    "per_page": 15,
    "total_items": 87,
    "total_pages": 6,
    "has_more": true,
    "next_cursor": "c3RhcnRfYWZ0ZXI9Y3VzXzAwMzA",
    "previous_cursor": "ZW5kX2JlZm9yZT1jdXNfMDAxNg",
    "links": {
      "self": "https://api.example.com/v2/customers?page=2&per_page=15",
      "next": "https://api.example.com/v2/customers?page=3&per_page=15",
      "prev": "https://api.example.com/v2/customers?page=1&per_page=15"
    }
  },
  "data": [
    {
      "id": "cus_0016",
      "object": "customer",
      "name": "Alder Creek Outfitters",
      "email": "accounts@alder.example.com",
      "phone": "+44 20 7946 0016",
      "status": "active",
      "created_at": "2025-03-14T09:21:00Z",
      "lifetime_value": {
        "amount": 18450.75,
        "currency": "GBP"
      },
      "address": {
        "line1": "14 Quayside Road",
        "line2": null,
        "city": "Leeds",
        "postal_code": "LS1 4DY",
        "country": "GB"
      },
      "tags": [
        "wholesale",
        "net-30"
      ],
      "metadata": {
        "account_manager": "Priya Raman",
        "tier": "gold"
      }
    },
    {
      "id": "cus_0017",
      "object": "customer",
      "name": "Bramble, Hart & Sons",
      "email": "accounts@bramble.example.com",
      "phone": "+44 20 7946 0017",
      "status": "active",
      "created_at": "2025-03-19T11:02:00Z",
      "lifetime_value": {
        "amount": 4210.45,
        "currency": "GBP"
      },
      "address": {
        "line1": "2 Minster Yard",
        "line2": null,
        "city": "York",
        "postal_code": "YO1 7HH",
        "country": "GB"
      },
      "tags": [
        "retail"
      ],
      "metadata": {
        "account_manager": "Daniel Okoro",
        "tier": "silver"
      }
    },
    {
      "id": "cus_0018",
      "object": "customer",
      "name": "Cobalt Marine Supply",
      "email": "accounts@cobalt.example.com",
      "phone": "+44 20 7946 0018",
      "status": "active",
      "created_at": "2025-04-02T08:45:00Z",
      "lifetime_value": {
        "amount": 52310.18,
        "currency": "GBP"
      },
      "address": {
        "line1": "Unit 7, Millbay Docks",
        "line2": null,
        "city": "Plymouth",
        "postal_code": "PL1 3EF",
        "country": "GB"
      },
      "tags": [
        "wholesale",
        "marine",
        "net-60"
      ],
      "metadata": {
        "account_manager": "Priya Raman",
        "tier": "platinum"
      }
    },
    {
      "id": "cus_0019",
      "object": "customer",
      "name": "Dunmore Garden Centre",
      "email": "accounts@dunmore.example.com",
      "phone": "+44 20 7946 0019",
      "status": "suspended",
      "created_at": "2025-04-11T15:30:00Z",
      "lifetime_value": {
        "amount": 1875.33,
        "currency": "GBP"
      },
      "address": {
        "line1": "88 Ripon Road",
        "line2": null,
        "city": "Harrogate",
        "postal_code": "HG1 2BU",
        "country": "GB"
      },
      "tags": [
        "retail",
        "seasonal"
      ],
      "metadata": {
        "account_manager": "Marta Lindqvist",
        "tier": "bronze"
      }
    },
    {
      "id": "cus_0020",
      "object": "customer",
      "name": "Eastgate Pharmacy Ltd",
      "email": "accounts@eastgate.example.com",
      "phone": "+44 20 7946 0020",
      "status": "active",
      "created_at": "2025-05-06T10:12:00Z",
      "lifetime_value": {
        "amount": 9634.27,
        "currency": "GBP"
      },
      "address": {
        "line1": "31 Eastgate Street",
        "line2": null,
        "city": "Chester",
        "postal_code": "CH1 1LF",
        "country": "GB"
      },
      "tags": [
        "healthcare",
        "priority"
      ],
      "metadata": {
        "account_manager": "Tomas Okafor",
        "tier": "silver"
      }
    },
    {
      "id": "cus_0021",
      "object": "customer",
      "name": "Fenwick, Lowe and Partners",
      "email": "accounts@fenwick.example.com",
      "phone": "+44 20 7946 0021",
      "status": "active",
      "created_at": "2025-05-21T13:40:00Z",
      "lifetime_value": {
        "amount": 12988.61,
        "currency": "GBP"
      },
      "address": {
        "line1": "5 Grey Street",
        "line2": null,
        "city": "Newcastle upon Tyne",
        "postal_code": "NE1 6EE",
        "country": "GB"
      },
      "tags": [
        "professional-services"
      ],
      "metadata": {
        "account_manager": "Daniel Okoro",
        "tier": "gold"
      }
    },
    {
      "id": "cus_0022",
      "object": "customer",
      "name": "Greyfield Bakery",
      "email": "accounts@greyfield.example.com",
      "phone": "+44 20 7946 0022",
      "status": "trial",
      "created_at": "2025-06-03T07:55:00Z",
      "lifetime_value": {
        "amount": 642.18,
        "currency": "GBP"
      },
      "address": {
        "line1": "19 Walcot Street",
        "line2": null,
        "city": "Bath",
        "postal_code": "BA1 5BN",
        "country": "GB"
      },
      "tags": [
        "food",
        "net-14"
      ],
      "metadata": {
        "account_manager": "Marta Lindqvist",
        "tier": "bronze"
      }
    },
    {
      "id": "cus_0023",
      "object": "customer",
      "name": "Harbourside \"Fresh\" Market",
      "email": "accounts@harbourside.example.com",
      "phone": "+44 20 7946 0023",
      "status": "active",
      "created_at": "2025-06-17T16:05:00Z",
      "lifetime_value": {
        "amount": 27415.09,
        "currency": "GBP"
      },
      "address": {
        "line1": "Canons Way",
        "line2": null,
        "city": "Bristol",
        "postal_code": "BS1 5LL",
        "country": "GB"
      },
      "tags": [
        "food",
        "wholesale",
        "priority"
      ],
      "metadata": {
        "account_manager": "Tomas Okafor",
        "tier": "gold"
      }
    },
    {
      "id": "cus_0024",
      "object": "customer",
      "name": "Ironbridge Tools",
      "email": "accounts@ironbridge.example.com",
      "phone": "+44 20 7946 0024",
      "status": "active",
      "created_at": "2025-07-08T09:18:00Z",
      "lifetime_value": {
        "amount": 15702.66,
        "currency": "GBP"
      },
      "address": {
        "line1": "Unit 3, Halesfield 9",
        "line2": null,
        "city": "Telford",
        "postal_code": "TF7 4QW",
        "country": "GB"
      },
      "tags": [
        "trade",
        "net-30"
      ],
      "metadata": {
        "account_manager": "Priya Raman",
        "tier": "gold"
      }
    },
    {
      "id": "cus_0025",
      "object": "customer",
      "name": "Juniper Lane Cafe",
      "email": "accounts@juniper.example.com",
      "phone": "+44 20 7946 0025",
      "status": "trial",
      "created_at": "2025-07-29T12:27:00Z",
      "lifetime_value": {
        "amount": 388.52,
        "currency": "GBP"
      },
      "address": {
        "line1": "47 Cowley Road",
        "line2": null,
        "city": "Oxford",
        "postal_code": "OX4 1HP",
        "country": "GB"
      },
      "tags": [
        "food"
      ],
      "metadata": {
        "account_manager": "Daniel Okoro",
        "tier": "bronze"
      }
    },
    {
      "id": "cus_0026",
      "object": "customer",
      "name": "Kestrel Print, Inc.",
      "email": "accounts@kestrel.example.com",
      "phone": "+44 20 7946 0026",
      "status": "active",
      "created_at": "2025-08-12T14:50:00Z",
      "lifetime_value": {
        "amount": 8120.37,
        "currency": "GBP"
      },
      "address": {
        "line1": "12 Friar Street",
        "line2": null,
        "city": "Reading",
        "postal_code": "RG1 1DB",
        "country": "GB"
      },
      "tags": [
        "trade",
        "eu-shipping"
      ],
      "metadata": {
        "account_manager": "Marta Lindqvist",
        "tier": "silver"
      }
    },
    {
      "id": "cus_0027",
      "object": "customer",
      "name": "Larchmont Florists",
      "email": "accounts@larchmont.example.com",
      "phone": "+44 20 7946 0027",
      "status": "active",
      "created_at": "2025-09-02T08:03:00Z",
      "lifetime_value": {
        "amount": 3054.91,
        "currency": "GBP"
      },
      "address": {
        "line1": "6 Bridge Street",
        "line2": null,
        "city": "Cambridge",
        "postal_code": "CB2 1UA",
        "country": "GB"
      },
      "tags": [
        "retail",
        "seasonal"
      ],
      "metadata": {
        "account_manager": "Tomas Okafor",
        "tier": "bronze"
      }
    },
    {
      "id": "cus_0028",
      "object": "customer",
      "name": "Meadowbank Dairy Co-op",
      "email": "accounts@meadowbank.example.com",
      "phone": "+44 20 7946 0028",
      "status": "active",
      "created_at": "2025-09-24T10:36:00Z",
      "lifetime_value": {
        "amount": 21967.42,
        "currency": "GBP"
      },
      "address": {
        "line1": "Meadowbank Farm, Lanark Road",
        "line2": null,
        "city": "Edinburgh",
        "postal_code": "EH14 2NE",
        "country": "GB"
      },
      "tags": [
        "food",
        "cooperative",
        "net-30"
      ],
      "metadata": {
        "account_manager": "Priya Raman",
        "tier": "gold"
      }
    },
    {
      "id": "cus_0029",
      "object": "customer",
      "name": "Northgate Veterinary Clinic",
      "email": "accounts@northgate.example.com",
      "phone": "+44 20 7946 0029",
      "status": "suspended",
      "created_at": "2025-10-15T15:14:00Z",
      "lifetime_value": {
        "amount": 5521.08,
        "currency": "GBP"
      },
      "address": {
        "line1": "102 Northgate",
        "line2": null,
        "city": "Darlington",
        "postal_code": "DL1 1RN",
        "country": "GB"
      },
      "tags": [
        "healthcare"
      ],
      "metadata": {
        "account_manager": "Daniel Okoro",
        "tier": "silver"
      }
    },
    {
      "id": "cus_0030",
      "object": "customer",
      "name": "Oakhurst Building Supplies",
      "email": "accounts@oakhurst.example.com",
      "phone": null,
      "status": "active",
      "created_at": "2025-11-04T09:09:00Z",
      "lifetime_value": {
        "amount": 33870.25,
        "currency": "EUR"
      },
      "address": {
        "line1": "Unit 21, Ballymount Industrial Estate",
        "line2": null,
        "city": "Dublin",
        "postal_code": "D12 X9Y2",
        "country": "IE"
      },
      "tags": [
        "trade",
        "eu-shipping",
        "net-60"
      ],
      "metadata": {
        "account_manager": "Tomas Okafor",
        "tier": "platinum"
      }
    }
  ],
  "meta": {
    "rate_limit": {
      "limit": 1000,
      "remaining": 987,
      "reset_at": "2026-11-20T15:00:00Z"
    },
    "deprecations": []
  }
}
```
