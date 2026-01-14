import frappe
import json
from dateutil import parser
from frappe.utils import get_time, getdate

def create_rista_branch(data):
	'''
		Method to create Rista Branch if not exists from API data
	'''
	branch_code = data.get('branchCode', '')
	branch_name = data.get('branchName', '')
	if branch_code and not frappe.db.exists('Rista Branch', branch_code):
		new_branch = frappe.get_doc({
			'doctype': 'Rista Branch',
			'branch_code': branch_code,
			'branch_name': branch_name
		})
		new_branch.insert()
	return branch_code

def create_rista_sales_log(data):
	'''
		Method to create Rista Invoice Log
	'''
	branch_code = data.get('branchCode', '')
	invoice_number = data.get('invoiceNumber', '')
	invoice_date = data.get('invoiceDate', '')
	dt = parser.isoparse(invoice_date)
	posting_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')

	if not frappe.db.exists('Rista Sales Log', { 'rista_branch': branch_code, 'invoice_number': invoice_number }):
		new_log = frappe.get_doc({
			'doctype': 'Rista Sales Log',
			'branch_code': branch_code,
			'invoice_number': invoice_number,
			'invoice_date': getdate(posting_datetime),
			'invoice_time': get_time(posting_datetime),
			'payload': json.dumps(data, indent=2)
		})
		new_log.insert()
		return new_log.name

def create_sales_invoice(data):
	'''
		Method to create Sales Invoice from Rista Sales Log
	'''
	try:
		invoice_no = data.get('invoiceNumber')
		invoice_date = data.get('invoiceDate')
		branch_code = data.get('branchCode', '')
		if not invoice_no or not invoice_date:
			return
		dt = parser.isoparse(invoice_date)
		posting_datetime = dt.strftime('%Y-%m-%d %H:%M:%S')
		default_customer = frappe.db.get_single_value('Rista Settings', 'default_customer')

		#Getting Company and Income Account
		company = frappe.db.get_single_value('Global Defaults', 'default_company')
		if frappe.db.exists('Rista Branch', branch_code):
			company = frappe.get_value('Rista Branch', branch_code, 'company')
		income_account = frappe.get_value('Company', company, 'default_income_account') or frappe.get_single_value('Accounts Settings', 'default_income_account')

		if not frappe.db.exists('Sales Invoice', { 'invoice_no':invoice_no }):
			#Creating Sales Invoice
			sales_invoice_doc = frappe.new_doc('Sales Invoice')
			sales_invoice_doc.company = company
			sales_invoice_doc.invoice_no = invoice_no
			sales_invoice_doc.posting_date = getdate(posting_datetime)
			sales_invoice_doc.due_date = getdate(posting_datetime)
			sales_invoice_doc.posting_time = get_time(posting_datetime)
			sales_invoice_doc.set_posting_time = 1
			sales_invoice_doc.customer = default_customer
			sales_invoice_doc.rista_branch = branch_code
			sales_invoice_doc.rista_invoice_number = invoice_no
			sales_invoice_doc.rista_channel = data.get('channel', '')
			sales_invoice_doc.rista_order_url = data.get('url', '')

			#Adding Items to Sales Invoice
			for item in data.get('items', []):
				item_code = ''
				rista_sku = item.get('skuCode', '')
				if frappe.db.exists('Item', { 'rista_item_code': rista_sku }):
					item_code = frappe.get_value('Item', { 'rista_item_code': rista_sku }, 'item_code')
				sales_invoice_doc.append('items', {
					'item_code': item_code,
					'item_name': item.get('shortName'),
					'qty': item.get('quantity'),
					'rate': item.get('unitPrice'),
					'amount': item.get('itemTotalAmount'),
					'income_account': income_account
				})

				#Handling Item Addons
				for addon in item.get('options', []):
					addon_sku = addon.get('skuCode', '')
					addon_item_code = ''
					if frappe.db.exists('Item', { 'rista_item_code': addon_sku }):
						addon_item_code = frappe.get_value('Item', { 'rista_item_code': addon_sku }, 'item_code')
					sales_invoice_doc.append('items', {
						'item_code': addon_item_code,
						'item_name': addon.get('itemName'),
						'qty': addon.get('quantity'),
						'rate': addon.get('unitPrice'),
						'amount': addon.get('amount'),
						'income_account': income_account
					})

			#Handling Taxes
			for tax in data.get('taxes', []):
				tax_name = tax.get('name')
				tax_percent = tax.get('percentage', 0)
				account_head = get_tax_account_head(tax_name, tax_percent, company)
				if not account_head:
					frappe.throw(f'Please set up Tax Account Head for Tax: {tax_name} ({tax_percent}%) in Rista GST Mapping')
				sales_invoice_doc.append('taxes', {
					'charge_type': 'Actual',
					'account_head': account_head,
					'description': tax.get('name'),
					'rate': tax.get('percentage', 0),
					'charge_type': 'Actual',
					'tax_amount': tax.get('amount', 0)
				})

			#Hanlding rounding adjustment
			sales_invoice_doc.disable_rounded_total = 1
			rounding_adjustment = data.get('roundOffAmount', 0)
			rounding_adjustment_account = frappe.db.get_single_value('Rista Settings', 'rounding_adjustment_account')
			if not rounding_adjustment_account:
				frappe.throw('Please set Rounding Adjustment Account in Rista Settings')
			if rounding_adjustment:
				sales_invoice_doc.append('taxes', {
					'charge_type': 'Actual',
					'account_head': rounding_adjustment_account,
					'description': 'Rounding Adjustment',
					'rate': 0,
					'charge_type': 'Actual',
					'tax_amount': rounding_adjustment
				})

			#Handling Discounts
			sales_invoice_doc.apply_discount_on = 'Net Total'
			sales_invoice_doc.discount_amount = abs(data.get('netDiscountAmount', 0))

			sales_invoice_doc.save(ignore_permissions=True)
			sales_invoice_doc.submit()

			return sales_invoice_doc.name
	except Exception as e:
		frappe.log_error(f'Error creating Sales Invoice from Rista Data: {str(e)}', 'Rista Sales Invoice Creation Error')
		return None

def get_tax_account_head(tax_name, tax_percent, company, type='Out State'):
	'''
		Method to get or create Tax Account Head
	'''
	account_head = ''
	filter_data = {
		'rista_account': tax_name,
		'tax_percent': tax_percent,
		'company': company,
		'type': type
	}
	if frappe.db.exists('Rista GST Mapping', filter_data):
		account_head = frappe.get_value('Rista GST Mapping', filter_data, 'account_head')
	return account_head

def get_mop_account(mode_of_payment, company):
	'''
		Method to get default account for a given Mode of Payment and Company
	'''
	result = frappe.db.sql('''
		SELECT default_account
		FROM `tabMode of Payment Account`
		WHERE parent=%s AND company=%s
		LIMIT 1
	''', (mode_of_payment, company), as_dict=True)
	return result[0].default_account if result else None
