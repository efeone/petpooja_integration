def get_item_custom_fields():
	'''
		Custom fields that need to be added to the Item DocType
	'''
	return {
		"Item": [
			{
				"fieldname": "petpooja_item_code",
				"fieldtype": "Data",
				"label": "Petpooja Item Code",
				"insert_after": "item_code",
				"unique": 1
			},
			{
				"fieldname": "rista_item_code",
				"fieldtype": "Data",
				"label": "Rista Item Code",
				"insert_after": "petpooja_item_code",
				"unique": 1
			}
		]
	}
