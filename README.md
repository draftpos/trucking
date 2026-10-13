# Trucking & Fleet Logistics Management Suite (trucking)

[![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20%7C%2018.0-714B67?logo=odoo&logoColor=white)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)
[![Category](https://img.shields.io/badge/Category-Operations%2FLogistics-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

> **Comprehensive Freight Haulage, Load Consignment, Fleet & Trailer Tracking, Cross-Border Transit, Fuel Advance Management & Profitability Analytics for Odoo.**

---

## 📌 Overview

**Trucking & Fleet Logistics Management Suite** is an enterprise-grade transportation management system (TMS) purpose-built for freight haulers, logistics brokers, and cross-border trucking operations. It unites load dispatching, carrier settlement, customer freight billing, route management, border clearances, and fuel advance tracking into a synchronized operational pipeline.

---

## ✨ Key Features

### 1. 🚛 Load Consignment & Dispatch Management
- End-to-end tracking of freight consignments: **Draft** ➔ **Confirmed** ➔ **In Transit** ➔ **Delivered** ➔ **Invoiced**.
- Multi-party billing: Generates customer freight invoices (`sale_management` / `account`) and carrier/driver expense bills (`purchase` / `account`) from the same load record.

### 2. 🚚 Fleet, Trailer & Driver Registry
- Complete tracking of commercial power units (horses/trucks), trailers (tri-axles, superlinks, flatbeds, tankers), and assigned drivers.
- License disc expirations, certificate of fitness (COF), and routine maintenance schedules.

### 3. ⛽ Comprehensive Fuel & Expense Management
- **Fuel Issuances & Advances**: Support for on-site bulk fuel bowser dispensations and en-route cash fuel advances.
- **Approval Workflows**: Dedicated wizards for fuel adjustments, top-ups, receipts, and exceptions without blocking load dispatch.
- **Default & Route-Based Expenses**: Pre-populate toll fees, driver allowances, and border charges based on selected origin and destination.

### 4. 🛂 Cross-Border & Customs Route Intelligence
- Configurable routes, waypoints, and transit times.
- **Border Clearance Tracking**: Monitor customs clearing agents, clearing status, and border delay durations across transit corridors.

### 5. 📈 Interactive Analytics & Customer Profitability
- Real-time OWL dashboard (`trucking_dashboard`) displaying active in-transit loads, revenue, fuel spend, and fleet utilization.
- Dedicated Customer & Load Profitability reports analyzing net margins per kilometer and per route.

---

## 🚀 Installation & Setup

1. **Clone or Copy** this repository into your Odoo custom addons directory:
   ```bash
   git clone git@github.com:draftpos/trucking.git trucking
   ```
2. **Update Addons List**:
   - Activate Developer Mode (`Settings` -> `General Settings` -> `Activate Developer Mode`).
   - Navigate to `Apps` -> `Update Apps List`.
3. **Install the Module**:
   - Search for **Trucking** (`trucking`).
   - Click **Install** or **Upgrade**.

---

## 📁 Technical Information

| Attribute | Value |
|---|---|
| **Technical Name** | `trucking` |
| **Category** | Logistics / Transportation |
| **Odoo Compatibility** | Odoo 17.0+ & 18.0+ |
| **Dependencies** | `base`, `web`, `sale_management`, `purchase`, `account`, `stock`, `hr_expense` |
| **License** | LGPL-3 |
| **Maintainer** | DraftPOS & Havano Solutions |

---

## 📄 License

This module is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3)**. See the [LICENSE](LICENSE) file for details.
