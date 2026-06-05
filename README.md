# Odoo Trucking App

## Overview

The **Odoo Trucking App** is a comprehensive Logistics & Fleet Management module designed for Odoo. It streamlines the management of trucking operations, giving logistics companies control over loads, transporters, customer billing, and vehicle scheduling—all from a centralized system.

## Key Features

- **Load Management**: End-to-end tracking of loads, including pickup, transit, and delivery statuses.
- **Fleet & Trailer Tracking**: Keep precise records of vehicles, trailers, and their assignments to specific routes or loads.
- **Route Optimization & Management**: Pre-configure standard routes for accurate pricing and transit times.
- **Transporter & Customer Billing**: Seamlessly integrates with Odoo Accounting (`sale_management`, `purchase`, `account`) to manage customer invoices and transporter payments simultaneously.
- **Custom Dashboard**: A dedicated, interactive JS/XML based dashboard (`trucking_dashboard`) providing a bird's-eye view of your logistics operations, fleet status, and financial metrics.
- **Interactive Wizards**: Features built-in wizards to handle exceptions natively, such as load rejections (`trucking_reject_wizard`), missing payments (`payment_load_warning_wizard`), and zero-confirmations (`trucking_zero_confirm_wizard`).

## Technical Information

- **Module Name**: `trucking`
- **Category**: Logistics
- **Dependencies**: `base`, `web`, `sale_management`, `purchase`, `account`, `havano_all_in_one`
- **Assets**: Includes custom SCSS, JS, and XML for the backend dashboard.

## Installation

1. Clone or download this repository into your Odoo `addons` directory.
2. Update your Odoo app list.
3. Search for **"Trucking"** in the Apps menu.
4. Click **Install**.

## Contribution

For contributions, please create a new branch, push your feature or bugfix, and submit a Pull Request.

---
*Developed by Havano*
