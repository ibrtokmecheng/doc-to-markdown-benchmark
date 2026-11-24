# gen-purchase-orders

Source file: gen-purchase-orders.json
Source type: JSON

## gen-purchase-orders

```json
{
  "export": {
    "system": "Northbank ERP",
    "report": "open_purchase_orders",
    "generated_at": "2026-05-28T06:00:00Z",
    "timezone": "Europe/London",
    "filters": {
      "status": [
        "approved",
        "partially_received"
      ],
      "order_date_from": "2026-05-01",
      "order_date_to": "2026-05-31"
    }
  },
  "purchase_orders": [
    {
      "po_number": "PO-2026-04118",
      "status": "approved",
      "order_date": "2026-05-04",
      "currency": "GBP",
      "supplier": {
        "id": "SUP-0042",
        "name": "Arden Castings",
        "contact": {
          "name": "Helen Marsh",
          "email": "orders@arden.example.com",
          "phone": "+44 114 496 0731"
        },
        "address": {
          "city": "Sheffield",
          "country": "GB"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "AC-1180",
          "description": "Pump housing, cast iron",
          "quantity": 120,
          "unit_price": 18.75,
          "amount": 2250.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-15",
            "site": "Sheffield",
            "dock": null
          }
        },
        {
          "line": 2,
          "sku": "AC-1192",
          "description": "Impeller cover, cast iron",
          "quantity": 120,
          "unit_price": 9.4,
          "amount": 1128.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-15",
            "site": "Sheffield",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 3378.0,
        "vat_rate": 0.2,
        "vat": 675.6,
        "gross": 4053.6
      },
      "approvals": [
        {
          "approver": "Priya Natarajan",
          "approved_at": "2026-05-05T09:12:44Z",
          "level": 1
        }
      ],
      "notes": null,
      "tags": [
        "castings",
        "framework-agreement"
      ]
    },
    {
      "po_number": "PO-2026-04127",
      "status": "partially_received",
      "order_date": "2026-05-06",
      "currency": "EUR",
      "supplier": {
        "id": "SUP-0057",
        "name": "Ødegaard Teknikk AS",
        "contact": {
          "name": "Lars Ødegaard",
          "email": "salg@odegaard.example.no",
          "phone": null
        },
        "address": {
          "city": "Bergen",
          "country": "NO"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "OT-5521",
          "description": "Gasket set \"Type B\", nitrile",
          "quantity": 400,
          "unit_price": 2.35,
          "amount": 940.0,
          "received_quantity": 250,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-05-29",
            "site": "Coventry",
            "dock": null
          }
        },
        {
          "line": 2,
          "sku": "OT-5530",
          "description": "Hydraulic hose 1/2 in, 2 m",
          "quantity": 60,
          "unit_price": 14.8,
          "amount": 888.0,
          "received_quantity": 60,
          "fully_received": true,
          "delivery": {
            "due_date": "2026-05-29",
            "site": "Coventry",
            "dock": null
          }
        },
        {
          "line": 3,
          "sku": "OT-5544",
          "description": "Quick coupling, steel",
          "quantity": 150,
          "unit_price": 6.15,
          "amount": 922.5,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-20",
            "site": "Coventry",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 2750.5,
        "vat_rate": 0.0,
        "vat": 0.0,
        "gross": 2750.5
      },
      "approvals": [
        {
          "approver": "Priya Natarajan",
          "approved_at": "2026-05-07T13:40:02Z",
          "level": 1
        }
      ],
      "notes": "Second delivery confirmed for week 25.",
      "tags": []
    },
    {
      "po_number": "PO-2026-04133",
      "status": "approved",
      "order_date": "2026-05-11",
      "currency": "EUR",
      "supplier": {
        "id": "SUP-0063",
        "name": "Müller & Söhne GmbH",
        "contact": {
          "name": "Jana Müller",
          "email": "vertrieb@mueller-soehne.example.de",
          "phone": "+49 203 555 0142"
        },
        "address": {
          "city": "Duisburg",
          "country": "DE"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "MS-0870",
          "description": "Hex bolt M8 x 40, zinc plated",
          "quantity": 5000,
          "unit_price": 0.13,
          "amount": 650.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-05",
            "site": "Sheffield",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 650.0,
        "vat_rate": 0.0,
        "vat": 0.0,
        "gross": 650.0
      },
      "approvals": [
        {
          "approver": "Daniel Brooks",
          "approved_at": "2026-05-11T16:03:19Z",
          "level": 1
        }
      ],
      "notes": null,
      "tags": [
        "fasteners"
      ]
    },
    {
      "po_number": "PO-2026-04141",
      "status": "approved",
      "order_date": "2026-05-14",
      "currency": "GBP",
      "supplier": {
        "id": "SUP-0071",
        "name": "Bexley Fasteners",
        "contact": {
          "name": "Tom Akers",
          "email": "sales@bexley.example.co.uk",
          "phone": "+44 24 7696 0218"
        },
        "address": {
          "city": "Coventry",
          "country": "GB"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "BF-2210",
          "description": "Spring washer M10",
          "quantity": 3000,
          "unit_price": 0.04,
          "amount": 120.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-02",
            "site": "Coventry",
            "dock": null
          }
        },
        {
          "line": 2,
          "sku": "BF-2234",
          "description": "Nyloc nut M10",
          "quantity": 3000,
          "unit_price": 0.07,
          "amount": 210.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-02",
            "site": "Coventry",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 330.0,
        "vat_rate": 0.2,
        "vat": 66.0,
        "gross": 396.0
      },
      "approvals": [
        {
          "approver": "Daniel Brooks",
          "approved_at": "2026-05-15T08:21:57Z",
          "level": 1
        }
      ],
      "notes": "Weekly call-off; see framework agreement FA-118.",
      "tags": [
        "fasteners",
        "call-off"
      ]
    },
    {
      "po_number": "PO-2026-04152",
      "status": "partially_received",
      "order_date": "2026-05-20",
      "currency": "GBP",
      "supplier": {
        "id": "SUP-0042",
        "name": "Arden Castings",
        "contact": {
          "name": "Helen Marsh",
          "email": "orders@arden.example.com",
          "phone": "+44 114 496 0731"
        },
        "address": {
          "city": "Sheffield",
          "country": "GB"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "AC-1205",
          "description": "Bearing housing, ductile iron",
          "quantity": 80,
          "unit_price": 27.6,
          "amount": 2208.0,
          "received_quantity": 40,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-25",
            "site": "Sheffield",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 2208.0,
        "vat_rate": 0.2,
        "vat": 441.6,
        "gross": 2649.6
      },
      "approvals": [
        {
          "approver": "Priya Natarajan",
          "approved_at": "2026-05-20T10:05:31Z",
          "level": 1
        }
      ],
      "notes": null,
      "tags": [
        "castings"
      ]
    },
    {
      "po_number": "PO-2026-04160",
      "status": "approved",
      "order_date": "2026-05-26",
      "currency": "EUR",
      "supplier": {
        "id": "SUP-0063",
        "name": "Müller & Söhne GmbH",
        "contact": {
          "name": "Jana Müller",
          "email": "vertrieb@mueller-soehne.example.de",
          "phone": "+49 203 555 0142"
        },
        "address": {
          "city": "Duisburg",
          "country": "DE"
        }
      },
      "lines": [
        {
          "line": 1,
          "sku": "MS-0912",
          "description": "Threaded rod M12, 1 m",
          "quantity": 250,
          "unit_price": 3.65,
          "amount": 912.5,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-30",
            "site": "Sheffield",
            "dock": null
          }
        },
        {
          "line": 2,
          "sku": "MS-0918",
          "description": "Anchor bolt M12 x 120",
          "quantity": 600,
          "unit_price": 1.48,
          "amount": 888.0,
          "received_quantity": 0,
          "fully_received": false,
          "delivery": {
            "due_date": "2026-06-30",
            "site": "Sheffield",
            "dock": null
          }
        }
      ],
      "totals": {
        "net": 1800.5,
        "vat_rate": 0.0,
        "vat": 0.0,
        "gross": 1800.5
      },
      "approvals": [
        {
          "approver": "Daniel Brooks",
          "approved_at": "2026-05-27T07:58:10Z",
          "level": 1
        }
      ],
      "notes": null,
      "tags": []
    }
  ],
  "summary": {
    "order_count": 6,
    "line_count": 11,
    "gross_by_currency": {
      "EUR": 5201.0,
      "GBP": 7099.2
    },
    "warnings": []
  }
}
```
