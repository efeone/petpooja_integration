def get_sales_invoice_custom_fields():
	'''
		Custom fields that need to be added to the Sales Invoice DocType
	'''
	return {
		"Sales Invoice": [
			{
				"fieldname": "petpooja_details",
				"fieldtype": "Section Break",
				"label": "Petpooja Details",
				"insert_after": "ignore_pricing_rule",
			},
			{
				"fieldname": "petpooja_order_id",
				"fieldtype": "Data",
				"label": "Petpooja Order ID",
				"insert_after": "petpooja_details",
				"read_only": 1,
			},
			{
				"fieldname": "petpooja_customer_invoice_id",
				"fieldtype": "Data",
				"label": "Petpooja Customer Invoice ID",
				"insert_after": "petpooja_order_id",
				"read_only": 1,
			},
			{
				"fieldname": "petpooja_cb1",
				"fieldtype": "Column Break",
				"insert_after": "petpooja_customer_invoice_id",
			},
			{
				"fieldname": "petpooja_order_type",
				"fieldtype": "Data",
				"label": "Petpooja Order Type",
				"insert_after": "petpooja_cb1",
				"read_only": 1,
			},
			{
				"fieldname": "petpooja_table_no",
				"fieldtype": "Data",
				"label": "Petpooja Table No.",
				"insert_after": "petpooja_order_type",
				"read_only": 1,
			}
		]
	}
