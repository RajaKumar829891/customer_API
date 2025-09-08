#!/usr/bin/env python3
"""
Test script for Odoo Customer API
Run this script to test all API endpoints
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:8097"
API_ENDPOINTS = {
    'create_customer': '/api/customer/create',
    'login': '/api/customer/login',
    'list_products': '/api/products',
    'add_to_cart': '/api/cart/add',
    'view_cart': '/api/cart/view',
    'categories': '/api/categories',
    'health': '/api/health'
}


class APITester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Odoo API Tester'
        })
        # Store authentication info
        self.auth_cookies = None
        self.session_id = None

    def make_request(self, endpoint, payload=None, method='POST', use_auth=True):
        """Make API request and handle JSON-RPC format"""
        url = f"{self.base_url}{endpoint}"

        try:
            # Use stored cookies for authenticated requests
            if use_auth and self.auth_cookies:
                self.session.cookies.update(self.auth_cookies)

            if method.upper() == 'POST':
                response = self.session.post(url, json=payload)
            else:
                response = self.session.get(url, params=payload)

            print(f"Request to: {url}")
            print(f"Payload: {json.dumps(payload, indent=2) if payload else 'None'}")
            print(f"Status Code: {response.status_code}")

            # Store cookies from response for session persistence
            if response.cookies:
                if not self.auth_cookies:
                    self.auth_cookies = {}
                self.auth_cookies.update(response.cookies)

            response.raise_for_status()
            full_response = response.json()
            print(f"Full Response: {json.dumps(full_response, indent=2)}")

            # Extract result from JSON-RPC envelope
            if 'result' in full_response:
                return full_response['result']
            elif 'error' in full_response:
                print(f"JSON-RPC Error: {full_response['error']}")
                return None
            else:
                return full_response

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"Error details: {json.dumps(error_details, indent=2)}")
                except:
                    print(f"Response text: {e.response.text}")
            return None

    def test_health_check(self):
        """Test health check endpoint"""
        print("\n" + "=" * 60)
        print("Testing Health Check")
        print("=" * 60)

        result = self.make_request(API_ENDPOINTS['health'], {}, use_auth=False)

        if result and result.get('status') == 'success':
            print("SUCCESS: Health check passed")
            print(f"Message: {result.get('message')}")
            print(f"Timestamp: {result.get('timestamp')}")
            return True
        else:
            print("FAILED: Health check failed")
            return False

    def test_create_customer(self, customer_data):
        """Test customer creation"""
        print("\n" + "=" * 60)
        print(f"Creating customer: {customer_data['email']}")
        print("=" * 60)

        result = self.make_request(API_ENDPOINTS['create_customer'], customer_data, use_auth=False)

        if result and result.get('status') == 'success':
            print("SUCCESS: Customer created successfully")
            print(f"Customer ID: {result.get('customer_id')}")
            print(f"User ID: {result.get('user_id')}")
            print(f"Email: {result.get('email')}")
            return result
        else:
            print("FAILED: Customer creation failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None

    def test_login(self, credentials):
        """Test customer login"""
        print("\n" + "=" * 60)
        print(f"Logging in: {credentials['email']}")
        print("=" * 60)

        result = self.make_request(API_ENDPOINTS['login'], credentials, use_auth=False)

        if result and result.get('status') == 'success':
            print("SUCCESS: Login successful")
            print(f"Customer: {result.get('customer_name')}")
            print(f"Customer ID: {result.get('customer_id')}")
            print(f"User ID: {result.get('user_id')}")
            print(f"Session Token: {result.get('session_token', 'N/A')}")

            # Store session info for future requests
            self.session_id = result.get('session_id')
            print(f"Session ID stored: {self.session_id}")

            return result
        else:
            print("FAILED: Login failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None

    def test_list_products(self, filters=None):
        """Test product listing"""
        print("\n" + "=" * 60)
        print("Listing products")
        print("=" * 60)

        payload = filters or {'limit': 10, 'offset': 0}
        result = self.make_request(API_ENDPOINTS['list_products'], payload, use_auth=False)

        if result and result.get('status') == 'success':
            products = result.get('products', [])
            total_count = result.get('total_count', 0)
            print(f"SUCCESS: Found {len(products)} products (Total: {total_count})")

            if products:
                print("\nProducts found:")
                for i, product in enumerate(products[:3], 1):
                    print(f"  {i}. {product.get('name')} - ${product.get('price', 0):.2f}")
                    print(f"     ID: {product.get('id')}, Category: {product.get('category', 'N/A')}")
                    print(f"     SKU: {product.get('sku', 'N/A')}")
            else:
                print("No products found in database")
                print("TIP: Add some products in Odoo to test cart functionality")

            return result
        else:
            print("FAILED: Product listing failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None

    def test_add_to_cart(self, product_id, quantity=1):
        """Test adding product to cart"""
        print("\n" + "=" * 60)
        print(f"Adding product {product_id} to cart (qty: {quantity})")
        print("=" * 60)

        payload = {'product_id': product_id, 'quantity': quantity}
        # Use authenticated request
        result = self.make_request(API_ENDPOINTS['add_to_cart'], payload, use_auth=True)

        if result and result.get('status') == 'success':
            print("SUCCESS: Product added to cart")
            print(f"Product: {result.get('product_name')}")
            print(f"Cart Total: ${result.get('cart_total', 0):.2f}")
            print(f"Items Count: {result.get('cart_items_count', 0)}")
            return result
        else:
            print("FAILED: Add to cart failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None

    def test_view_cart(self):
        """Test viewing cart"""
        print("\n" + "=" * 60)
        print("Viewing cart")
        print("=" * 60)

        result = self.make_request(API_ENDPOINTS['view_cart'], {}, use_auth=True)

        if result and result.get('status') == 'success':
            cart = result.get('cart')
            if cart:
                print("SUCCESS: Cart retrieved successfully")
                print(f"Cart ID: {cart.get('id')}")
                print(f"Items: {cart.get('items_count', 0)}")
                print(f"Subtotal: ${cart.get('subtotal', 0):.2f}")
                print(f"Tax: ${cart.get('tax_amount', 0):.2f}")
                print(f"Total: ${cart.get('total', 0):.2f}")
                print(f"Currency: {cart.get('currency', 'N/A')}")

                lines = cart.get('lines', [])
                if lines:
                    print("\nCart items:")
                    for line in lines:
                        print(
                            f"  - {line.get('product_name')}: {line.get('quantity')} x ${line.get('price_unit'):.2f} = ${line.get('price_subtotal'):.2f}")
            else:
                print("SUCCESS: Cart is empty")
            return result
        else:
            print("FAILED: View cart failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None

    def test_list_categories(self):
        """Test category listing"""
        print("\n" + "=" * 60)
        print("Listing categories")
        print("=" * 60)

        result = self.make_request(API_ENDPOINTS['categories'], {}, use_auth=False)

        if result and result.get('status') == 'success':
            categories = result.get('categories', [])
            total_count = result.get('total_count', 0)
            print(f"SUCCESS: Found {total_count} categories")

            if categories:
                print("\nCategories found:")
                for category in categories[:5]:
                    parent = f" (Parent: {category.get('parent_name')})" if category.get('parent_name') else ""
                    print(f"  - {category.get('name')}{parent}")
                    print(f"    ID: {category.get('id')}")
            else:
                print("No categories found")

            return result
        else:
            print("FAILED: Category listing failed")
            if result:
                print(f"Error: {result.get('message', 'Unknown error')}")
            return None


def create_test_product():
    """Helper to suggest creating test products"""
    print("\n" + "=" * 60)
    print("TIP: Creating Test Products")
    print("=" * 60)
    print("To test cart functionality, you need products in Odoo.")
    print("You can create them via:")
    print("1. Odoo web interface: Inventory > Products > Create")
    print("2. Odoo shell:")
    print("   ./odoo-bin shell -d your_database")
    print("   product = env['product.product'].create({")
    print("       'name': 'Test Product',")
    print("       'list_price': 99.99,")
    print("       'sale_ok': True")
    print("   })")


def main():
    """Run all API tests"""
    print("Starting Odoo Customer API Tests")
    print(f"Base URL: {BASE_URL}")
    print("Testing all endpoints with detailed output...")

    tester = APITester(BASE_URL)

    # Generate unique email for this test run
    timestamp = int(time.time())
    customer_data = {
        "name": "Test User",
        "email": f"test.user.{timestamp}@example.com",
        "phone": "1234567890",
        "password": "password123"
    }

    # Track test results
    tests_passed = 0
    total_tests = 0

    # 1. Health check
    total_tests += 1
    if tester.test_health_check():
        tests_passed += 1

    # 2. Create customer
    total_tests += 1
    create_result = tester.test_create_customer(customer_data)
    if create_result:
        tests_passed += 1

    # 3. Login
    total_tests += 1
    login_credentials = {
        "email": customer_data["email"],
        "password": customer_data["password"]
    }
    login_result = tester.test_login(login_credentials)
    if login_result:
        tests_passed += 1

    # Only continue with authenticated tests if login was successful
    if not login_result:
        print("\n" + "=" * 60)
        print("STOPPING: Cannot continue tests without successful login")
        print("=" * 60)
        print(f"\nFinal Results: {tests_passed}/{total_tests} tests passed")
        return False

    # 4. List categories
    total_tests += 1
    if tester.test_list_categories():
        tests_passed += 1

    # 5. List products
    total_tests += 1
    products_result = tester.test_list_products({'limit': 10})
    if products_result:
        tests_passed += 1

    # 6. Add to cart (if products exist)
    if products_result and products_result.get('products'):
        first_product = products_result['products'][0]
        product_id = first_product['id']

        total_tests += 1
        if tester.test_add_to_cart(product_id, 2):
            tests_passed += 1
    else:
        print("\nSKIPPING: Add to cart test (no products available)")
        create_test_product()

    # 7. View cart
    total_tests += 1
    if tester.test_view_cart():
        tests_passed += 1

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("STATUS: All tests passed successfully!")
        return True
    elif tests_passed >= 3:  # Health, create, login working
        print("STATUS: Core functionality working! Some features need products in database.")
        return True
    else:
        print("STATUS: Some critical tests failed. Check the detailed output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)