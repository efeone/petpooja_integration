def get_company_custom_fields():
	'''
		Custom fields that need to be added to the Company DocType
	'''
	return {
		"Company": [
			{
				"fieldname": "petpooja_restaurant_id",
				"fieldtype": "Data",
				"label": "Petpooja Restaurant ID",
				"insert_after": "tax_id",
				"unique": 1
			}
		]
	}
