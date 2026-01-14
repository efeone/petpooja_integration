# Copyright (c) 2026, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RistaSalesLog(Document):
	def after_insert(self):
		self.handle_invoice_creation()

	def handle_invoice_creation(self):
		'''
			Handle Sales Invoice creation after Rista Sales Log is created
		'''
		frappe.enqueue("petpooja_integration.rista_integration.rista_apis.sync_sales_invoice", invoice_id=self.invoice_number, queue='long')
