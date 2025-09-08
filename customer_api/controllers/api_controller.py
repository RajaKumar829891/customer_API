# controllers/api_controller.py
import json
import logging
from odoo import http, fields
from odoo.http import request
from werkzeug.exceptions import BadRequest, Unauthorized
from odoo.exceptions import ValidationError, AccessError
import hashlib
import secrets
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class CustomerAPIController(http.Controller):

    def _get_json_data(self):
        """Helper method to extract JSON data from request"""
        try:
            # For Odoo 17, try multiple ways to get JSON data
            if hasattr(request, 'get_json_data'):
                return request.get_json_data()
            elif hasattr(request, 'jsonrequest'):
                return request.jsonrequest
            elif request.httprequest.is_json:
                return request.httprequest.get_json()
            else:
                # Fallback: read raw data and parse
                raw_data = request.httprequest.get_data()
                if raw_data:
                    return json.loads(raw_data.decode('utf-8'))
                return {}
        except Exception as e:
            _logger.error(f"Error getting JSON data: {e}")
            return {}

    @http.route('/api/customer/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_customer(self, **kw):
        """
        Create a new customer
        Expected payload: {
            "name": "Customer Name",
            "email": "customer@example.com",
            "phone": "1234567890",
            "password": "password123"
        }
        """
        try:
            # Get JSON data from request
            data = self._get_json_data()
            _logger.info(f"Received data for customer creation: {data}")

            # If data is empty, try kw as fallback
            if not data:
                data = kw
                _logger.info(f"Using kw data: {data}")

            # Validate required fields
            required_fields = ['name', 'email', 'password']
            for field in required_fields:
                if not data.get(field):
                    return {'status': 'error', 'message': f'Missing required field: {field}'}

            # Validate email format
            email = data['email'].strip().lower()
            if not email or '@' not in email:
                return {'status': 'error', 'message': 'Invalid email format'}

            # Check if email already exists
            existing_partner = request.env['res.partner'].sudo().search([
                ('email', '=', email),
                ('is_company', '=', False)
            ], limit=1)

            if existing_partner:
                return {'status': 'error', 'message': 'Email already exists'}

            # Check if user with this login already exists
            existing_user = request.env['res.users'].sudo().search([
                ('login', '=', email)
            ], limit=1)

            if existing_user:
                return {'status': 'error', 'message': 'User with this email already exists'}

            # Create the customer
            partner_vals = {
                'name': data['name'].strip(),
                'email': email,
                'phone': data.get('phone', '').strip(),
                'is_company': False,
                'customer_rank': 1,
                'supplier_rank': 0,
            }

            partner = request.env['res.partner'].sudo().create(partner_vals)

            # Create user account for login
            user_vals = {
                'name': data['name'].strip(),
                'login': email,
                'email': email,
                'partner_id': partner.id,
                'password': data['password'],
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                'active': True,
            }

            user = request.env['res.users'].sudo().create(user_vals)

            return {
                'status': 'success',
                'message': 'Customer created successfully',
                'customer_id': partner.id,
                'user_id': user.id,
                'email': email
            }

        except ValidationError as e:
            _logger.error(f"Validation error creating customer: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            _logger.error(f"Error creating customer: {str(e)}")
            return {'status': 'error', 'message': 'Internal server error'}

    @http.route('/api/customer/login', type='json', auth='public', methods=['POST'], csrf=False)
    def customer_login(self, **kw):
        """
        Login customer using email and password
        Expected payload: {
            "email": "customer@example.com",
            "password": "password123"
        }
        """
        try:
            # Get JSON data from request
            data = self._get_json_data()
            _logger.info(f"Received data for login: {data}")

            # If data is empty, try kw as fallback
            if not data:
                data = kw
                _logger.info(f"Using kw data: {data}")

            if not data.get('email') or not data.get('password'):
                return {'status': 'error', 'message': 'Email and password are required'}

            email = data['email'].strip().lower()
            password = data['password']

            # Try to authenticate user
            try:
                uid = request.session.authenticate(request.db, email, password)
            except Exception as auth_error:
                _logger.error(f"Authentication error: {str(auth_error)}")
                return {'status': 'error', 'message': 'Invalid email or password'}

            if not uid:
                return {'status': 'error', 'message': 'Invalid email or password'}

            # Get user and partner information
            user = request.env['res.users'].sudo().browse(uid)
            partner = user.partner_id

            # Check if user has portal access
            if not user.has_group('base.group_portal') and not user.has_group('base.group_user'):
                return {'status': 'error', 'message': 'Access denied'}

            # Generate session token (optional, for API authentication)
            session_token = secrets.token_hex(32)

            return {
                'status': 'success',
                'message': 'Login successful',
                'user_id': uid,
                'customer_id': partner.id,
                'customer_name': partner.name,
                'customer_email': partner.email,
                'session_token': session_token,
                'session_id': request.session.sid
            }

        except Exception as e:
            _logger.error(f"Error during login: {str(e)}")
            return {'status': 'error', 'message': 'Login failed'}


class ProductAPIController(http.Controller):

    def _get_json_data(self):
        """Helper method to extract JSON data from request"""
        try:
            if hasattr(request, 'get_json_data'):
                return request.get_json_data()
            elif hasattr(request, 'jsonrequest'):
                return request.jsonrequest
            elif request.httprequest.is_json:
                return request.httprequest.get_json()
            else:
                raw_data = request.httprequest.get_data()
                if raw_data:
                    return json.loads(raw_data.decode('utf-8'))
                return {}
        except Exception as e:
            _logger.error(f"Error getting JSON data: {e}")
            return {}

    @http.route('/api/products', type='json', auth='public', methods=['POST'], csrf=False)
    def list_products(self, **kw):
        """
        List available products
        Optional parameters: {
            "limit": 20,
            "offset": 0,
            "category_id": 1,
            "search": "product name"
        }
        """
        try:
            data = self._get_json_data()
            if not data:
                data = kw

            # Build domain for product search
            domain = [
                ('sale_ok', '=', True),
                ('active', '=', True)
            ]

            # Add category filter if provided
            if data.get('category_id'):
                try:
                    category_id = int(data['category_id'])
                    domain.append(('categ_id', '=', category_id))
                except (ValueError, TypeError):
                    return {'status': 'error', 'message': 'Invalid category_id format'}

            # Add search filter if provided
            if data.get('search'):
                search_term = data['search'].strip()
                if search_term:
                    domain.append('|')
                    domain.append(('name', 'ilike', search_term))
                    domain.append(('default_code', 'ilike', search_term))

            # Get limit and offset
            try:
                limit = min(int(data.get('limit', 20)), 100)  # Max 100 products per request
                offset = max(int(data.get('offset', 0)), 0)
            except (ValueError, TypeError):
                return {'status': 'error', 'message': 'Invalid limit or offset format'}

            # Search products
            products = request.env['product.product'].sudo().search(
                domain, limit=limit, offset=offset, order='name asc'
            )

            # Format product data
            product_list = []
            base_url = request.httprequest.host_url.rstrip('/')

            for product in products:
                # Get product images
                image_url = f'{base_url}/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None

                # Get stock quantity (if inventory module is installed)
                try:
                    stock_qty = product.qty_available
                except:
                    stock_qty = 0

                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description_sale or product.description or '',
                    'price': float(product.list_price),
                    'currency': product.currency_id.name if product.currency_id else request.env.company.currency_id.name,
                    'category': product.categ_id.name if product.categ_id else '',
                    'category_id': product.categ_id.id if product.categ_id else None,
                    'available_qty': stock_qty,
                    'image_url': image_url,
                    'uom': product.uom_id.name if product.uom_id else '',
                    'sku': product.default_code or '',
                    'is_available': product.sale_ok and product.active,
                }
                product_list.append(product_data)

            # Get total count
            total_count = request.env['product.product'].sudo().search_count(domain)

            return {
                'status': 'success',
                'products': product_list,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            }

        except Exception as e:
            _logger.error(f"Error listing products: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve products'}


class CartAPIController(http.Controller):

    def _get_json_data(self):
        """Helper method to extract JSON data from request"""
        try:
            if hasattr(request, 'get_json_data'):
                return request.get_json_data()
            elif hasattr(request, 'jsonrequest'):
                return request.jsonrequest
            elif request.httprequest.is_json:
                return request.httprequest.get_json()
            else:
                raw_data = request.httprequest.get_data()
                if raw_data:
                    return json.loads(raw_data.decode('utf-8'))
                return {}
        except Exception as e:
            _logger.error(f"Error getting JSON data: {e}")
            return {}

    def _authenticate_session(self):
        """Check if user is authenticated"""
        if not request.uid or request.uid == request.env.ref('base.public_user').id:
            return False
        return True

    def _get_or_create_cart(self, partner_id):
        """Get existing cart or create new one"""
        # Look for existing draft sale order (cart)
        cart = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'draft'),
        ], limit=1, order='write_date desc')

        if not cart:
            # Create new cart
            cart_vals = {
                'partner_id': partner_id,
                'state': 'draft',
            }
            cart = request.env['sale.order'].sudo().create(cart_vals)

        return cart

    @http.route('/api/cart/add', type='json', auth='public', methods=['POST'], csrf=False)
    def add_to_cart(self, **kw):
        """
        Add product to cart
        Expected payload: {
            "product_id": 1,
            "quantity": 2
        }
        """
        try:
            data = self._get_json_data()
            if not data:
                data = kw

            # Check authentication
            if not self._authenticate_session():
                return {'status': 'error', 'message': 'Authentication required'}

            if not data.get('product_id'):
                return {'status': 'error', 'message': 'Product ID is required'}

            try:
                product_id = int(data['product_id'])
                quantity = float(data.get('quantity', 1))
            except (ValueError, TypeError):
                return {'status': 'error', 'message': 'Invalid product_id or quantity format'}

            if quantity <= 0:
                return {'status': 'error', 'message': 'Quantity must be greater than 0'}

            # Get current user's partner
            user = request.env.user
            partner = user.partner_id

            # Validate product exists and is sellable
            product = request.env['product.product'].sudo().browse(product_id)
            if not product.exists() or not product.sale_ok or not product.active:
                return {'status': 'error', 'message': 'Product not found or not available for sale'}

            # Get or create cart
            cart = self._get_or_create_cart(partner.id)

            # Check if product already in cart
            existing_line = cart.order_line.filtered(lambda l: l.product_id.id == product_id)

            if existing_line:
                # Update quantity
                existing_line[0].product_uom_qty += quantity
            else:
                # Add new line
                line_vals = {
                    'order_id': cart.id,
                    'product_id': product_id,
                    'product_uom_qty': quantity,
                }
                request.env['sale.order.line'].sudo().create(line_vals)

            # Trigger recomputation
            cart._amount_all()

            return {
                'status': 'success',
                'message': 'Product added to cart successfully',
                'cart_id': cart.id,
                'cart_total': float(cart.amount_total),
                'cart_items_count': len(cart.order_line),
                'product_name': product.name
            }

        except Exception as e:
            _logger.error(f"Error adding to cart: {str(e)}")
            return {'status': 'error', 'message': 'Failed to add product to cart'}

    @http.route('/api/cart/view', type='json', auth='public', methods=['POST'], csrf=False)
    def view_cart(self, **kw):
        """View current user's cart"""
        try:
            # Check authentication
            if not self._authenticate_session():
                return {'status': 'error', 'message': 'Authentication required'}

            user = request.env.user
            partner = user.partner_id

            # Get current cart
            cart = request.env['sale.order'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'draft'),
            ], limit=1, order='write_date desc')

            if not cart:
                return {
                    'status': 'success',
                    'cart': None,
                    'message': 'Cart is empty'
                }

            # Format cart data
            cart_lines = []
            base_url = request.httprequest.host_url.rstrip('/')

            for line in cart.order_line:
                line_data = {
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'product_sku': line.product_id.default_code or '',
                    'quantity': line.product_uom_qty,
                    'price_unit': float(line.price_unit),
                    'price_subtotal': float(line.price_subtotal),
                    'price_total': float(line.price_total),
                    'image_url': f'{base_url}/web/image/product.product/{line.product_id.id}/image_1920' if line.product_id.image_1920 else None
                }
                cart_lines.append(line_data)

            cart_data = {
                'id': cart.id,
                'name': cart.name,
                'lines': cart_lines,
                'subtotal': float(cart.amount_untaxed),
                'tax_amount': float(cart.amount_tax),
                'total': float(cart.amount_total),
                'currency': cart.currency_id.name,
                'items_count': len(cart.order_line),
                'partner_name': partner.name
            }

            return {
                'status': 'success',
                'cart': cart_data
            }

        except Exception as e:
            _logger.error(f"Error viewing cart: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve cart'}


# Additional utility endpoints
class UtilityAPIController(http.Controller):

    def _get_json_data(self):
        """Helper method to extract JSON data from request"""
        try:
            if hasattr(request, 'get_json_data'):
                return request.get_json_data()
            elif hasattr(request, 'jsonrequest'):
                return request.jsonrequest
            elif request.httprequest.is_json:
                return request.httprequest.get_json()
            else:
                raw_data = request.httprequest.get_data()
                if raw_data:
                    return json.loads(raw_data.decode('utf-8'))
                return {}
        except Exception as e:
            _logger.error(f"Error getting JSON data: {e}")
            return {}

    @http.route('/api/categories', type='json', auth='public', methods=['POST'], csrf=False)
    def list_categories(self, **kw):
        """List product categories"""
        try:
            categories = request.env['product.category'].sudo().search([])

            category_list = []
            for category in categories:
                category_data = {
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id.id if category.parent_id else None,
                    'parent_name': category.parent_id.name if category.parent_id else None,
                    'complete_name': category.complete_name
                }
                category_list.append(category_data)

            return {
                'status': 'success',
                'categories': category_list,
                'total_count': len(category_list)
            }

        except Exception as e:
            _logger.error(f"Error listing categories: {str(e)}")
            return {'status': 'error', 'message': 'Failed to retrieve categories'}

    @http.route('/api/health', type='json', auth='public', methods=['POST'], csrf=False)
    def health_check(self, **kw):
        """API health check endpoint"""
        return {
            'status': 'success',
            'message': 'API is working',
            'timestamp': fields.Datetime.now().isoformat(),
            'odoo_version': '17.0'
        }