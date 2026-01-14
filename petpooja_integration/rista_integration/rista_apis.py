import frappe
import time
import jwt
import requests
from dateutil import parser
from frappe.utils.data import today, getdate

#Utils Methods
from petpooja_integration.utils import create_rista_branch
from petpooja_integration.utils import create_rista_sales_log
from petpooja_integration.utils import create_sales_invoice
from petpooja_integration.utils import get_mop_account

#API Key and Secret
API_KEY = frappe.db.get_single_value('Rista Settings', 'api_key')
BASE_URL = frappe.db.get_single_value('Rista Settings', 'api_base_url')
API_SECRET = frappe.utils.password.get_decrypted_password('Rista Settings', 'Rista Settings', 'secret_key')

@frappe.whitelist()
def sync_branches():
	'''
		Method to sync branches from Rista to ERPNext
	'''
	try:
		# Token creation time (seconds)
		token_creation_time = int(time.time())

		# JWT payload
		payload = {
			'iss': API_KEY,
			'iat': token_creation_time
		}

		# Generate JWT (HS256 default)
		token = jwt.encode(payload, API_SECRET, algorithm='HS256')

		url = '{0}/branch/list'.format(BASE_URL)

		headers = {
			'x-api-key': API_KEY,
			'x-api-token': token,
			'Content-Type': 'application/json'
		}

		response = requests.get(url, headers=headers)
		data = response.json()

		if response.status_code != 200:
			if data.get("message"):
				return f'API Error {response.status_code}: {data.get("message")}'
			return f'API Error Occured with statud code {response.status_code}'
		for d in data:
			create_rista_branch(d)
		return 'Branches synced successfully.'

	except Exception as e:
		return f'Error syncing branches: {str(e)}'

@frappe.whitelist()
def sync_sales_data(posting_date=today()):
	'''
		Method to sync sales data from Rista to ERPNext for all branches
	'''
	branches = frappe.db.get_all('Rista Branch', pluck='name')
	for branch in branches:
		sync_branch_sales_data(branch, posting_date)

@frappe.whitelist()
def sync_branch_sales_data(branch_code, posting_date=today()):
	'''
		Method to sync sales data from Rista to ERPNext for a specific branch
	'''
	# Token creation time (seconds)
	token_creation_time = int(time.time())

	# JWT payload
	payload = {
		"iss": API_KEY,
		"iat": token_creation_time
	}

	# API Arguments
	args = {
		"branch": branch_code,
		"day": posting_date
	}

	sales_data = []
	last_key = ''
	while True:
		if last_key:
			args['lastKey'] = last_key
		# Generate JWT (HS256 default)
		token = jwt.encode(payload, API_SECRET, algorithm="HS256")

		url = "{0}/sales/summary".format(BASE_URL)

		headers = {
			"x-api-key": API_KEY,
			"x-api-token": token,
			"Content-Type": "application/json"
		}

		response = requests.get(url, headers=headers, params=args)
		data = response.json()

		if response.status_code != 200:
			if data.get("message"):
				return f'API Error {response.status_code}: {data.get("message")}'
			return f'API Error Occured with statud code {response.status_code}'
		if data.get('data', []):
			sales_data.extend(data.get('data', []))
		if data.get('lastKey'):
			last_key = data.get('lastKey')
		else:
			break
	for sale in sales_data:
		create_rista_sales_log(sale)
	return 'Sales Invoices synced successfully.'

@frappe.whitelist()
def sync_sales_invoice(invoice_id):
	'''
		Method to sync a specific sales invoice from Rista to ERPNext
	'''
	# Token creation time (seconds)
	token_creation_time = int(time.time())

	# JWT payload
	payload = {
		"iss": API_KEY,
		"iat": token_creation_time
	}

	# API Arguments
	args = {
		"invoice": invoice_id,
	}

	# Generate JWT (HS256 default)
	token = jwt.encode(payload, API_SECRET, algorithm="HS256")

	url = "{0}/sale".format(BASE_URL)

	headers = {
		"x-api-key": API_KEY,
		"x-api-token": token,
		"Content-Type": "application/json"
	}

	response = requests.get(url, headers=headers, params=args)
	data = response.json()
	if response.status_code != 200:
		if data.get("message"):
			return f'API Error {response.status_code}: {data.get("message")}'
		return f'API Error Occured with statud code {response.status_code}'
	invoice = create_sales_invoice(data)
	payments = data.get('payments', [])
	if invoice and payments:
		handle_payments(invoice, payments)
	return 'Sales Invoices synced successfully.'

def handle_payments(sales_invoice, payments):
	'''
		Method to handle payments for Sales Invoice
	'''
	try:
		if not frappe.db.exists('Sales Invoice', sales_invoice):
			return
		sales_invoice_doc = frappe.get_doc('Sales Invoice', sales_invoice)
		for payment in payments:
			pay_mode = payment.get('mode', )
			mode_of_payment = ''
			if frappe.db.exists('Mode of Payment', { 'rista_payment_type': pay_mode }):
				mode_of_payment = frappe.get_value('Mode of Payment', { 'rista_payment_type': pay_mode }, 'name')
			if not mode_of_payment:
				sales_invoice_doc.add_comment(
					'Comment', 
					'Mode of Payment mapping not found for {0}, Skipped Payment Entry creation.'.format(frappe.bold(pay_mode))
				)
				continue
			amount = payment.get('amount', 0)
			dt = parser.isoparse(payment.get('postedDate'))
			posting_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
			company = sales_invoice_doc.company
			mop_account = get_mop_account(mode_of_payment, company)
			if not mop_account:
				sales_invoice_doc.add_comment(
					'Comment',
					'Default account not found for Mode of Payment {0}, Skipped Payment Entry creation.'.format(frappe.bold(mode_of_payment))
				)
				continue
			payment_entry = frappe.new_doc('Payment Entry')
			payment_entry.party_type = 'Customer'
			payment_entry.party = sales_invoice_doc.customer
			payment_entry.payment_type = 'Receive'
			payment_entry.company = company
			payment_entry.posting_date = getdate(posting_datetime)
			payment_entry.mode_of_payment = mode_of_payment
			payment_entry.paid_from = sales_invoice_doc.debit_to
			payment_entry.paid_to = mop_account
			payment_entry.paid_amount = amount
			payment_entry.received_amount = amount
			payment_entry.reference_no = sales_invoice_doc.rista_invoice_number
			payment_entry.reference_date = getdate(posting_datetime)
			payment_entry.append('references', {
				'reference_doctype': 'Sales Invoice',
				'reference_name': sales_invoice,
				'outstanding_amount': frappe.db.get_value('Sales Invoice', sales_invoice, 'outstanding_amount'),
				'allocated_amount': amount
			})
			payment_entry.save(ignore_permissions=True)
			payment_entry.submit()
	except Exception as e:
		sales_invoice_doc.add_comment(
			'Comment',
			'Error creating Payment Entry: {0}'.format(frappe.bold(str(e)))
		)