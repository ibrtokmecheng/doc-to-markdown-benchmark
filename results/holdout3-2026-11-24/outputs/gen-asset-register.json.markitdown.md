{
  "register": {
    "site": "Larkspur Business Park",
    "exported_at": "2027-04-02T08:15:00-07:00",
    "asset_count": 8,
    "source": "CMMS export, schema 3.2",
    "currency": "USD"
  },
  "assets": [
    {
      "tag": "AHU-A-03",
      "description": "Air handling unit, rooftop",
      "category": "HVAC",
      "location": {
        "building": "A",
        "floor": "Roof",
        "room": null
      },
      "manufacturer": "Nordvent Systems",
      "model": "NV-4200",
      "serial": "NV42-19-00871",
      "installed": "2019-06-14",
      "in_service": true,
      "specs": {
        "airflow_cfm": 12000,
        "motor_hp": 15,
        "filter_size": "24 x 24 x 4 in"
      },
      "warranty": null,
      "service_history": [
        {
          "date": "2027-01-12",
          "work_order": "WO-27-0112",
          "summary": "Belt replaced, bearings greased",
          "cost_usd": 412.5
        },
        {
          "date": "2027-03-01",
          "work_order": "WO-27-1040",
          "summary": "Quarterly filter change",
          "cost_usd": 286.0
        }
      ],
      "replacement_cost_usd": 86500,
      "tags": [
        "critical",
        "rooftop"
      ]
    },
    {
      "tag": "CH-A-01",
      "description": "Centrifugal chiller, 400 tons",
      "category": "HVAC",
      "location": {
        "building": "A",
        "floor": "Roof",
        "room": "Chiller plant"
      },
      "manufacturer": "Kessler & Mohr Kältetechnik GmbH",
      "model": "KM-C400",
      "serial": "C400-2027-0016",
      "installed": "2027-05-20",
      "in_service": false,
      "specs": {
        "capacity_tons": 400,
        "refrigerant": "R-1233zd"
      },
      "warranty": {
        "provider": "Kessler & Mohr Kältetechnik GmbH",
        "expires": "2032-05-19",
        "parts_only": false
      },
      "service_history": [],
      "replacement_cost_usd": 1150000,
      "tags": [
        "critical",
        "capital project CP-27-01"
      ]
    },
    {
      "tag": "GEN-D-01",
      "description": "Diesel emergency generator, 750 kW",
      "category": "Electrical",
      "location": {
        "building": "D",
        "floor": "Ground",
        "room": "Generator yard"
      },
      "manufacturer": "Halvorsen Power",
      "model": "HP-750D",
      "serial": "HP750-17-3321",
      "installed": "2017-11-02",
      "in_service": true,
      "specs": {
        "output_kw": 750,
        "fuel_tank_gal": 1200,
        "runtime_hours": 1843.6
      },
      "warranty": null,
      "service_history": [
        {
          "date": "2027-02-17",
          "work_order": "WO-27-0388",
          "summary": "Load bank test, 2 hours at 75 percent",
          "cost_usd": 1980.0
        }
      ],
      "replacement_cost_usd": 412000,
      "tags": [
        "critical",
        "life safety"
      ]
    },
    {
      "tag": "ELV-B-02",
      "description": "Traction elevator, car 2",
      "category": "Elevators",
      "location": {
        "building": "B",
        "floor": "All",
        "room": null
      },
      "manufacturer": "Summit Vertical Transport",
      "model": "ST-3500",
      "serial": "ST35-09-7710",
      "installed": "2009-08-28",
      "in_service": true,
      "specs": {
        "capacity_lb": 3500,
        "speed_fpm": 350,
        "stops": 4
      },
      "warranty": null,
      "service_history": [
        {
          "date": "2027-03-04",
          "work_order": "WO-27-0952",
          "summary": "Releveling adjusted at lobby",
          "cost_usd": 0
        }
      ],
      "replacement_cost_usd": 365000,
      "tags": [
        "capital project CP-27-05"
      ]
    },
    {
      "tag": "FACP-A-01",
      "description": "Fire alarm control panel",
      "category": "Life safety",
      "location": {
        "building": "A",
        "floor": "Ground",
        "room": "Fire command room"
      },
      "manufacturer": "Keystone Fire Protection",
      "model": "KF-8000",
      "serial": "KF8-27-0451",
      "installed": "2027-04-26",
      "in_service": true,
      "specs": {
        "loops": 4,
        "devices": 612
      },
      "warranty": {
        "provider": "Keystone Fire Protection",
        "expires": "2030-04-25",
        "parts_only": true
      },
      "service_history": [],
      "replacement_cost_usd": 92500,
      "tags": [
        "life safety"
      ]
    },
    {
      "tag": "WH-C-02",
      "description": "Gas water heater, 100 gal",
      "category": "Plumbing",
      "location": {
        "building": "C",
        "floor": "Ground",
        "room": "Café kitchen"
      },
      "manufacturer": "Aquafort",
      "model": "AF-100G",
      "serial": "AF1-21-55870",
      "installed": "2021-03-09",
      "in_service": true,
      "specs": {
        "capacity_gal": 100,
        "input_btu": 199900,
        "setpoint": "60 °C"
      },
      "warranty": {
        "provider": "Aquafort",
        "expires": "2027-03-08",
        "parts_only": true
      },
      "service_history": [
        {
          "date": "2026-12-03",
          "work_order": "WO-26-9917",
          "summary": "Replaced 3/4\" relief valve",
          "cost_usd": 168.4
        }
      ],
      "replacement_cost_usd": 14800,
      "tags": []
    },
    {
      "tag": "UPS-D-01",
      "description": "Uninterruptible power supply, 300 kVA",
      "category": "Electrical",
      "location": {
        "building": "D",
        "floor": "Ground",
        "room": "Data hall 1"
      },
      "manufacturer": "Halvorsen Power",
      "model": "HP-UPS300",
      "serial": "U300-18-0042",
      "installed": "2018-10-15",
      "in_service": true,
      "specs": {
        "rating_kva": 300,
        "battery_strings": 4,
        "battery_install": "2027-03-12"
      },
      "warranty": null,
      "service_history": [],
      "replacement_cost_usd": 238000,
      "tags": [
        "critical",
        "capital project CP-27-07"
      ]
    },
    {
      "tag": "RTU-B-05",
      "description": "Packaged rooftop unit, fitness center",
      "category": "HVAC",
      "location": {
        "building": "B",
        "floor": "Roof",
        "room": null
      },
      "manufacturer": "Nordvent Systems",
      "model": "NV-RTU15",
      "serial": "NVR15-14-2209",
      "installed": "2014-07-01",
      "in_service": true,
      "specs": {
        "cooling_tons": 15,
        "heating": "gas",
        "economizer": true
      },
      "warranty": null,
      "service_history": [],
      "replacement_cost_usd": 47250,
      "tags": [
        "rooftop"
      ]
    }
  ]
}
