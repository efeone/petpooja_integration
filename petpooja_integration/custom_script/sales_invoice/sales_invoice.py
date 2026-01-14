import frappe

def after_insert(doc, method):
	'''
		Method to handle actions after Sales Invoice insertion.
	'''
	link_to_rista_sales_log(doc)

def on_submit(doc, method):
	'''
		Method to handle actions on Sales Invoice submission.
	'''
	if doc.update_stock:
		for item in doc.items:
			handle_bom_stock_update(item.item_code, item.qty, item.warehouse)

def handle_bom_stock_update(item_code, qty, warehouse):
	'''
		Function to handle stock update for BOM items.
	'''
	bom = frappe.get_all('BOM', filters={'item': item_code, 'is_active': 1, 'is_default': 1}, fields=['name'])
	if bom:
		bom_doc = frappe.get_doc('BOM', bom[0].name)
		stock_entry = frappe.new_doc('Stock Entry')
		stock_entry.stock_entry_type = 'Material Issue'
		for bom_item in bom_doc.items:
			required_qty = bom_item.qty * qty
			stock_entry.append('items', {
				'item_code': bom_item.item_code,
				'qty': required_qty,
				's_warehouse': warehouse
			})
		stock_entry.save(ignore_permissions=True)
		stock_entry.submit()

def link_to_rista_sales_log(doc):
	'''
		Function to link Sales Invoice to Rista Sales Log if applicable.
	'''
	if doc.rista_invoice_number and doc.rista_branch:
		if frappe.db.exists('Rista Sales Log', {
			'invoice_number': doc.rista_invoice_number,
			'branch_code': doc.rista_branch,
		}):
			log = frappe.db.get_value('Rista Sales Log', {
				'invoice_number': doc.rista_invoice_number,
				'branch_code': doc.rista_branch,
			}, 'name')
			frappe.db.set_value('Rista Sales Log', log, 'sales_invoice_reference', doc.name, update_modified=False)