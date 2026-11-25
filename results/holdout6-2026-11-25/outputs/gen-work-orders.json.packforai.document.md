# gen-work-orders

Source file: gen-work-orders.json
Source type: JSON

## gen-work-orders

```json
{
  "meta": {
    "api_version": "2.3",
    "generated_at": "2031-05-14T06:00:12Z",
    "property": {
      "code": "HHH-SEA",
      "name": "Halcyon Harbor Seattle Waterfront"
    },
    "page": 1,
    "per_page": 10,
    "total": 10
  },
  "data": [
    {
      "id": "WO-31-05812",
      "type": "corrective",
      "priority": "urgent",
      "status": "completed",
      "location": {
        "building": "Tower",
        "floor": 7,
        "room": "712"
      },
      "asset": {
        "tag": "HVAC-0712",
        "category": "PTAC unit"
      },
      "reported_by": {
        "role": "guest",
        "channel": "phone"
      },
      "opened_at": "2031-05-03T22:14:00Z",
      "closed_at": "2031-05-03T23:40:00Z",
      "labor": [
        {
          "technician": "Mateus Andrade",
          "hours": 1.25
        }
      ],
      "parts": [
        {
          "sku": "THM-220",
          "description": "Thermistor, 10 kOhm",
          "qty": 1,
          "unit_cost": 18.4
        }
      ],
      "guest_impact": true,
      "notes": "Unit tripped its breaker; replaced the \"room sensor\" lead."
    },
    {
      "id": "WO-31-05815",
      "type": "preventive",
      "priority": "routine",
      "status": "completed",
      "location": {
        "building": "Tower",
        "floor": 1,
        "room": null
      },
      "asset": {
        "tag": "BLR-02",
        "category": "Hot water boiler"
      },
      "reported_by": null,
      "opened_at": "2031-05-04T07:00:00Z",
      "closed_at": "2031-05-04T10:30:00Z",
      "labor": [
        {
          "technician": "Zoë Lindqvist",
          "hours": 2.5
        },
        {
          "technician": "Mateus Andrade",
          "hours": 1.0
        }
      ],
      "parts": [],
      "guest_impact": false,
      "checklist": {
        "template": "PM-BLR-Q",
        "items": 14,
        "failed": 0
      }
    },
    {
      "id": "WO-31-05821",
      "type": "corrective",
      "priority": "high",
      "status": "on_hold",
      "location": {
        "building": "Garden Wing",
        "floor": 2,
        "room": "214"
      },
      "asset": {
        "tag": "PLB-214-TUB",
        "category": "Bathtub drain"
      },
      "reported_by": {
        "role": "housekeeping",
        "channel": "app"
      },
      "opened_at": "2031-05-05T09:42:00Z",
      "closed_at": null,
      "labor": [],
      "parts": [],
      "guest_impact": true,
      "hold_reason": "Waiting for a replacement drain body from the supplier",
      "room_out_of_order": true
    },
    {
      "id": "WO-31-05826",
      "type": "inspection",
      "priority": "routine",
      "status": "completed",
      "location": {
        "building": "Tower",
        "floor": 12,
        "room": null
      },
      "asset": {
        "tag": "ELV-03",
        "category": "Passenger elevator"
      },
      "reported_by": null,
      "opened_at": "2031-05-06T13:00:00Z",
      "closed_at": "2031-05-06T14:15:00Z",
      "labor": [
        {
          "technician": "Tadeusz Wróbel",
          "hours": 1.25
        }
      ],
      "parts": [],
      "guest_impact": false,
      "contractor": {
        "name": "Cascade Lift Services",
        "permit": "ELV-2031-118"
      }
    },
    {
      "id": "WO-31-05830",
      "type": "corrective",
      "priority": "urgent",
      "status": "completed",
      "location": {
        "building": "Podium",
        "floor": 0,
        "room": "Kitchen"
      },
      "asset": {
        "tag": "KIT-WIC-1",
        "category": "Walk-in cooler"
      },
      "reported_by": {
        "role": "chef",
        "channel": "radio"
      },
      "opened_at": "2031-05-07T05:51:00Z",
      "closed_at": "2031-05-07T08:05:00Z",
      "labor": [
        {
          "technician": "Zoë Lindqvist",
          "hours": 2.25
        }
      ],
      "parts": [
        {
          "sku": "GSK-WIC-36",
          "description": "Door gasket, 36 x 80 in",
          "qty": 1,
          "unit_cost": 96.0
        },
        {
          "sku": "HNG-HD-2",
          "description": "Heavy-duty hinge",
          "qty": 2,
          "unit_cost": 41.75
        }
      ],
      "guest_impact": false,
      "temperature_log": [
        41.2,
        39.8,
        37.9,
        36.5
      ]
    },
    {
      "id": "WO-31-05834",
      "type": "corrective",
      "priority": "high",
      "status": "completed",
      "location": {
        "building": "Garden Wing",
        "floor": 3,
        "room": "305"
      },
      "asset": {
        "tag": "LCK-305",
        "category": "Guest room door lock"
      },
      "reported_by": {
        "role": "front desk",
        "channel": "app"
      },
      "opened_at": "2031-05-08T19:20:00Z",
      "closed_at": "2031-05-08T19:55:00Z",
      "labor": [
        {
          "technician": "Tadeusz Wróbel",
          "hours": 0.5
        }
      ],
      "parts": [
        {
          "sku": "BAT-AA-4",
          "description": "AA batteries, pack of 4",
          "qty": 1,
          "unit_cost": 3.6
        }
      ],
      "guest_impact": true,
      "notes": null
    },
    {
      "id": "WO-31-05839",
      "type": "project",
      "priority": "planned",
      "status": "in_progress",
      "location": {
        "building": "Tower",
        "floor": 9,
        "room": null
      },
      "asset": null,
      "reported_by": null,
      "opened_at": "2031-05-09T08:00:00Z",
      "closed_at": null,
      "labor": [
        {
          "technician": "Mateus Andrade",
          "hours": 6.0
        },
        {
          "technician": "Ngozi Eze",
          "hours": 6.0
        }
      ],
      "parts": [],
      "guest_impact": false,
      "project": {
        "code": "RNV-SEA-09",
        "phase": "punch list"
      }
    },
    {
      "id": "WO-31-05843",
      "type": "corrective",
      "priority": "routine",
      "status": "cancelled",
      "location": {
        "building": "Tower",
        "floor": 4,
        "room": "418"
      },
      "asset": {
        "tag": "TV-418",
        "category": "Television"
      },
      "reported_by": {
        "role": "guest",
        "channel": "phone"
      },
      "opened_at": "2031-05-10T21:03:00Z",
      "closed_at": "2031-05-10T21:20:00Z",
      "labor": [],
      "parts": [],
      "guest_impact": false,
      "cancel_reason": "Guest found the input button; no fault"
    },
    {
      "id": "WO-31-05847",
      "type": "preventive",
      "priority": "routine",
      "status": "scheduled",
      "location": {
        "building": "Podium",
        "floor": -1,
        "room": "Pool plant"
      },
      "asset": {
        "tag": "POOL-PMP-1",
        "category": "Pool circulation pump"
      },
      "reported_by": null,
      "opened_at": "2031-05-11T06:00:00Z",
      "closed_at": null,
      "labor": [],
      "parts": [],
      "guest_impact": false,
      "due_by": "2031-05-18"
    },
    {
      "id": "WO-31-05851",
      "type": "corrective",
      "priority": "urgent",
      "status": "completed",
      "location": {
        "building": "Garden Wing",
        "floor": 1,
        "room": "Lobby"
      },
      "asset": {
        "tag": "DR-LBY-AUTO",
        "category": "Automatic sliding door"
      },
      "reported_by": {
        "role": "security",
        "channel": "radio"
      },
      "opened_at": "2031-05-12T23:48:00Z",
      "closed_at": "2031-05-13T01:10:00Z",
      "labor": [
        {
          "technician": "Ngozi Eze",
          "hours": 1.5
        }
      ],
      "parts": [
        {
          "sku": "SNS-MW-1",
          "description": "Motion sensor, microwave type",
          "qty": 1,
          "unit_cost": 212.5
        }
      ],
      "guest_impact": true,
      "notes": "Door stuck open; lobby staffed by security until repaired."
    }
  ],
  "links": {
    "self": "https://api.halcyon-harbor.example/v2/work-orders?page=1",
    "next": null
  }
}
```
