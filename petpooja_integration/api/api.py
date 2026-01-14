import frappe
from frappe.utils import getdate, get_time
from petpooja_integration.utils import get_mop_account

@frappe.whitelist(allow_guest=True)
def response(message, data, success, status_code):
	'''
		method to generates responses of an API
		args:
			message : response message string
			data : json object of the data
			success : True or False depending on the API response
			status_code : status of the request
	'''
	frappe.clear_messages()
	frappe.local.response['message'] = message
	frappe.local.response['data'] = data
	frappe.local.response['success'] = success
	frappe.local.response['http_status_code'] = status_code
	return

@frappe.whitelist(allow_guest=True)
def create_invoice():
	'''
		APIs to create Sales Invoice form Petpooja Orders
	'''
	try:
		enable_petpooja_apis = frappe.db.get_single_value('Petpooja Settings', 'enable_petpooja_apis')
		if not enable_petpooja_apis:
			return response('Petpooja APIs are disabled', {}, False, 403)

		data = frappe.form_dict
		if data.get('cmd'):
			data.pop('cmd')

		if not data.get('token'):
			return response('`token` is required', {}, False, 400)

		if data.get('token') != get_access_token():
			return response('Authentication failed, Invalid Access Token', {}, False, 401)

		if not data.get('properties'):
			return response('Invalid Request `properties` is a required parameter', {}, False, 400)
		data = data.get('properties')

		order_details = data.get('Order', {})
		if not order_details:
			return response('Order details not found', {}, False, 404)

		#Checking if Invoice already exists for the order
		if frappe.db.exists('Sales Invoice', { 'petpooja_order_id': order_details.get('orderID') }):
			invoice_id = frappe.get_value('Sales Invoice', { 'petpooja_order_id': order_details.get('orderID') }, 'name')
			response_data = { 
				'petpooja_order_id': order_details.get('orderID'),
				'invoice_id':invoice_id
			}
			return response('Invoice already exists for this order', response_data, False, 402)

		#Get Items
		items = get_formatted_items(data.get('OrderItem', []))
		if not items:
			return response('No items found in the order', {}, False, 404)

		#Checking Company existence
		company = get_company(data.get('Restaurant', {}))
		if not company:
			return response('Company not found for the given Restaurant', {}, False, 404)

		#Getting Customer
		customer = get_customer(data.get('Customer', {}))
		if not customer:
			return response('Customer not found and could not be created', {}, False, 404)

		#Set user to Administrator for creating documents		
		frappe.set_user('Administrator')

		posting_date = order_details.get('created_on')
		income_account = frappe.get_value('Company', company, 'default_income_account') or frappe.get_single_value('Accounts Settings', 'default_income_account')
		service_charge_item = frappe.db.get_single_value('Petpooja Settings', 'service_charge_item')
		packing_charge_item = frappe.db.get_single_value('Petpooja Settings', 'packing_charge_item')
		rounding_adjustment_account = frappe.db.get_single_value('Petpooja Settings', 'rounding_adjustment_account')
		update_stock = frappe.db.get_single_value('Petpooja Settings', 'update_stock')

		#Creating Sales Invoice
		sales_invoice_doc = frappe.new_doc('Sales Invoice')
		sales_invoice_doc.company = company
		sales_invoice_doc.customer = customer
		sales_invoice_doc.set_posting_time = 1
		sales_invoice_doc.due_date = getdate(posting_date)
		sales_invoice_doc.posting_date = getdate(posting_date)
		sales_invoice_doc.posting_time = get_time(posting_date)
		sales_invoice_doc.petpooja_order_id = order_details.get('orderID')
		sales_invoice_doc.petpooja_customer_invoice_id = order_details.get('customer_invoice_id')
		sales_invoice_doc.petpooja_order_type = order_details.get('order_type')
		sales_invoice_doc.petpooja_table_no = order_details.get('table_no')
		sales_invoice_doc.update_stock = update_stock

		#Adding Items to Sales Invoice
		for item in items:
			sales_invoice_doc.append('items', {
				'item_code': item.get('item_code'),
				'item_name': item.get('item_name'),
				'qty': item.get('quantity'),
				'rate': item.get('rate'),
				'amount': item.get('amount'),
				'income_account': income_account
			})

		#Adding Service Charge if available
		if order_details.get('service_charge'):
			sales_invoice_doc.append('items',{
				'item_code': service_charge_item,
				'item_name': 'Service Charge',
				'qty': 1,
				'rate': order_details.get('service_charge'),
				'amount': order_details.get('service_charge'),
				'income_account': income_account
			})

		#Adding Packing Charge if available
		if order_details.get('packaging_charge'):
			sales_invoice_doc.append('items',{
				'item_code': packing_charge_item,
				'item_name': 'Packing Charge',
				'qty': 1,
				'rate': order_details.get('packaging_charge'),
				'amount': order_details.get('packaging_charge'),
				'income_account': income_account
			})

		#Hanlde Discout if any
		if order_details.get('discount_total'):
			sales_invoice_doc.apply_discount_on = 'Net Total'
			sales_invoice_doc.discount_amount = order_details.get('discount_total')

		#Handle Rounding Adjustment if any
		if order_details.get('round_off'):
			sales_invoice_doc.append('taxes',{
				'charge_type': 'Actual',
				'account_head': rounding_adjustment_account,
				'description': 'Rounding Adjustment',
				'tax_amount': order_details.get('round_off'),
			})

		sales_invoice_doc.disable_rounded_total = 1
		sales_invoice_doc.save(ignore_permissions=True)
		sales_invoice_doc.submit()

		#Handle Payment Settlement
		handle_payment(sales_invoice_doc.name, order_details)

		response('Invoice created', { 'doc':sales_invoice_doc.as_dict() }, True, 200)

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'Petpooja Integration Error')
		response('Something went wrong', {}, False, 500)

def get_access_token():
	'''
		Method to get Petpooja Access Token
	'''
	return frappe.utils.password.get_decrypted_password(
		'Petpooja Settings', 'Petpooja Settings', 'access_token'
	)

def get_company(data):
	'''
		Method to get company based on restaurant data
	'''
	company = None
	if data.get('restID'):
		# Get Restaurant ID
		rest_id = data.get('restID')
		if frappe.db.exists('Company', {'petpooja_restaurant_id': rest_id}):
			company = frappe.get_value('Company', {'petpooja_restaurant_id': rest_id}, 'name')
	return company

def get_customer(data):
	'''
		Method to get customer based on customer data
	'''
	customer = frappe.db.get_single_value('Petpooja Settings', 'default_customer')
	create_customers = frappe.db.get_single_value('Petpooja Settings', 'create_customers')
	if data.get('name') and create_customers:
		customer_details = ''
		customer_doc = frappe.new_doc('Customer')
		customer_doc.customer_name = data.get('name')
		customer_doc.customer_type = 'Individual'
		#Append addional Info if available
		if data.get('address'):
			customer_details += f"Address: {data.get('address')}\n"
		if data.get('phone'):
			customer_details += f"Phone: {data.get('phone')}\n"
		if data.get('gstin'):
			customer_details += f"GSTIN: {data.get('gstin')}"
		customer_doc.customer_details = customer_details
		customer_doc.save(ignore_permissions=True)
		customer = customer_doc.name
	return customer

def get_formatted_items(items):
	'''
		Method to format items received from Petpooja to ERPNext Sales Invoice Items
	'''
	formatted_items = []
	for item in items:
		item_code = ''
		petpooja_item_code = item.get('itemcode')
		if frappe.db.exists('Item', {'petpooja_item_code': petpooja_item_code}):
			item_code = frappe.get_value('Item', {'petpooja_item_code': petpooja_item_code}, 'name')
		formatted_item = {
			'item_code': item_code,
			'item_name': item.get('name'),
			'qty': item.get('quantity'),
			'rate': item.get('price'),
			'amount': item.get('total')
		}
		formatted_items.append(formatted_item)
	return formatted_items

def handle_payment(sales_invoice, order_details):
	'''
		Method to handle payment entry against the created Sales Invoice
	'''
	try:
		if frappe.db.exists('Sales Invoice', sales_invoice):
			sales_invoice_doc = frappe.get_doc('Sales Invoice', sales_invoice)

			#Getting Payment Methods
			payment_methods = []
			if order_details.get('part_payments', []):
				for part_payment in order_details.get('part_payments', []):
					payment_methods.append({
						'method': part_payment.get('payment_type'),
						'amount': part_payment.get('amount')
					})
			else:
				payment_methods.append({
					'method': order_details.get('payment_type'),
					'amount': order_details.get('total')
				})

			#Creating Payment Entry for each payment method
			for mode in payment_methods:
				mode_of_payment = ''
				if frappe.db.exists('Mode of Payment', { 'petpooja_payment_type': mode.get('method') }):
					mode_of_payment = frappe.get_value('Mode of Payment', { 'petpooja_payment_type': mode.get('method') }, 'name')
				if not mode_of_payment:
					sales_invoice_doc.add_comment(
						'Comment',
						'Mode of Payment mapping not found for {0}, Skipped Payment Entry creation.'.format(frappe.bold(mode.get('method')))
					)
					continue

				mode_of_payment_account = get_mop_account(mode_of_payment, sales_invoice_doc.company)
				if not mode_of_payment_account:
					sales_invoice_doc.add_comment(
						'Comment',
						'Default account not found for Mode of Payment {0}, Skipped Payment Entry creation.'.format(frappe.bold(mode_of_payment))
					)
					continue

				payment_entry = frappe.new_doc('Payment Entry')
				payment_entry.payment_type = 'Receive'
				payment_entry.posting_date = getdate(order_details.get('created_on'))
				payment_entry.party_type = 'Customer'
				payment_entry.party = sales_invoice_doc.customer
				payment_entry.reference_no = order_details.get('orderID')
				payment_entry.reference_date = getdate(order_details.get('created_on'))
				payment_entry.mode_of_payment = mode_of_payment
				payment_entry.paid_from = sales_invoice_doc.debit_to
				payment_entry.paid_to = mode_of_payment_account
				payment_entry.received_amount = mode.get('amount')
				payment_entry.paid_amount = mode.get('amount')
				payment_entry.append('references', {
					'reference_doctype': 'Sales Invoice',
					'reference_name': sales_invoice,
					'allocated_amount': mode.get('amount'),
					'outstanding_amount': frappe.get_value('Sales Invoice', sales_invoice, 'outstanding_amount'),
					'paid_amount': mode.get('amount')
				})
				payment_entry.save(ignore_permissions=True)
				payment_entry.submit()
	except Exception as e:
		sales_invoice_doc.add_comment('Comment', 'Error while creating Payment Entry: {0}'.format(frappe.bold(str(e))))
