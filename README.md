# Customer API - Odoo Module

A comprehensive REST API module for Odoo 17.0 that provides customer management and e-commerce functionality.

## Features

- **Customer Management**: Create and authenticate customers
- **Product Management**: List products with filtering and search
- **Shopping Cart**: Add products to cart and manage cart contents
- **Categories**: Browse product categories
- **Health Check**: API status monitoring

## Installation

1. Copy the `customer_api` module to your Odoo addons directory
2. Restart your Odoo server
3. Go to Apps menu and install "Customer API" module
4. The API endpoints will be available at your Odoo instance URL

## API Endpoints

### Customer Management

#### Create Customer
- **Endpoint**: `POST /api/customer/create`
- **Type**: JSON
- **Auth**: Public

#### Customer Login
- **Endpoint**: `POST /api/customer/login`
- **Type**: JSON
- **Auth**: Public

### Product Management

#### List Products
- **Endpoint**: `POST /api/products`
- **Type**: JSON
- **Auth**: Public

### Shopping Cart

#### Add to Cart
- **Endpoint**: `POST /api/cart/add`
- **Type**: JSON
- **Auth**: Required

#### View Cart
- **Endpoint**: `POST /api/cart/view`
- **Type**: JSON
- **Auth**: Required

### Utility Endpoints

#### List Categories
- **Endpoint**: `POST /api/categories`
- **Type**: JSON
- **Auth**: Public

#### Health Check
- **Endpoint**: `POST /api/health`
- **Type**: JSON
- **Auth**: Public

## Usage

All API endpoints expect JSON data and return JSON responses. Check the API collection for detailed request/response examples.

## Dependencies

- Odoo 17.0
- base
- sale
- website
- product
- portal
- website_sale
- auth_signup

## License

LGPL-3

## Author

RajaKumar829891

## Support

For issues and questions, please create an issue in this repository.
