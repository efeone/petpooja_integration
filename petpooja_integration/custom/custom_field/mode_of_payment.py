def get_mode_of_payment_custom_fields():
	'''
		Custom fields that need to be added to the Mode of Payment DocType
	'''
	return {
		"Mode of Payment": [
			{
				"fieldname": "petpooja_payment_type",
				"fieldtype": "Data",
				"label": "Petpooja Payment Type",
				"insert_after": "type",
			}
		]
	}
