# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import json

import frappe
from frappe.core.doctype.doctype.doctype import InvalidFieldNameError
from frappe.core.doctype.doctype.test_doctype import new_doctype
from frappe.custom.doctype.customize_form.customize_form import reset_customization
from frappe.test_runner import make_test_records_for_doctype
from frappe.tests.utils import FrappeTestCase

test_dependencies = ["Custom Field", "Property Setter"]


class TestCustomizeForm(FrappeTestCase):
	def insert_custom_field(self):
		frappe.delete_doc_if_exists("Custom Field", "Event-test_custom_field")
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Event",
				"label": "Test Custom Field",
				"description": "A Custom Field for Testing",
				"fieldtype": "Select",
				"in_list_view": 1,
				"options": "\nCustom 1\nCustom 2\nCustom 3",
				"default": "Custom 3",
				"insert_after": frappe.get_meta("Event").fields[-1].fieldname,
			}
		).insert()

	def setUp(self):
		self.insert_custom_field()
		frappe.db.delete("Property Setter", dict(doc_type="Event"))
		frappe.db.commit()
		frappe.clear_cache(doctype="Event")

	def tearDown(self):
		frappe.delete_doc("Custom Field", "Event-test_custom_field")
		frappe.db.commit()
		frappe.clear_cache(doctype="Event")

	def get_customize_form(self, doctype=None):
		d = frappe.get_doc("Customize Form")
		if doctype:
			d.doc_type = doctype
		d.run_method("fetch_to_customize")
		return d

	def test_fetch_to_customize(self):
		d = self.get_customize_form()
		self.assertEqual(d.doc_type, None)
		self.assertEqual(len(d.get("fields")), 0)

		d = self.get_customize_form("Event")
		self.assertEqual(d.doc_type, "Event")
		self.assertEqual(len(d.get("fields")), 38)

		d = self.get_customize_form("Event")
		self.assertEqual(d.doc_type, "Event")

		self.assertEqual(len(d.get("fields")), len(frappe.get_doc("DocType", d.doc_type).fields) + 1)
		self.assertEqual(d.get("fields")[-1].fieldname, "test_custom_field")
		self.assertEqual(d.get("fields", {"fieldname": "event_type"})[0].in_list_view, 1)

		return d

	def test_save_customization_property(self):
		d = self.get_customize_form("Event")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter", {"doc_type": "Event", "property": "allow_copy"}, "value"
			),
			None,
		)

		d.allow_copy = 1
		d.run_method("save_customization")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter", {"doc_type": "Event", "property": "allow_copy"}, "value"
			),
			"1",
		)

		d.allow_copy = 0
		d.run_method("save_customization")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter", {"doc_type": "Event", "property": "allow_copy"}, "value"
			),
			None,
		)

	def test_save_customization_field_property(self):
		d = self.get_customize_form("Event")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Event", "property": "reqd", "field_name": "repeat_this_event"},
				"value",
			),
			None,
		)

		repeat_this_event_field = d.get("fields", {"fieldname": "repeat_this_event"})[0]
		repeat_this_event_field.reqd = 1
		d.run_method("save_customization")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Event", "property": "reqd", "field_name": "repeat_this_event"},
				"value",
			),
			"1",
		)

		repeat_this_event_field = d.get("fields", {"fieldname": "repeat_this_event"})[0]
		repeat_this_event_field.reqd = 0
		d.run_method("save_customization")
		self.assertEqual(
			frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Event", "property": "reqd", "field_name": "repeat_this_event"},
				"value",
			),
			None,
		)

	def test_save_customization_custom_field_property(self):
		d = self.get_customize_form("Event")
		self.assertEqual(frappe.db.get_value("Custom Field", "Event-test_custom_field", "reqd"), 0)

		custom_field = d.get("fields", {"fieldname": "test_custom_field"})[0]
		custom_field.reqd = 1
		custom_field.no_copy = 1
		d.run_method("save_customization")
		self.assertEqual(frappe.db.get_value("Custom Field", "Event-test_custom_field", "reqd"), 1)
		self.assertEqual(frappe.db.get_value("Custom Field", "Event-test_custom_field", "no_copy"), 1)

		custom_field = d.get("fields", {"is_custom_field": True})[0]
		custom_field.reqd = 0
		custom_field.no_copy = 0
		d.run_method("save_customization")
		self.assertEqual(frappe.db.get_value("Custom Field", "Event-test_custom_field", "reqd"), 0)
		self.assertEqual(frappe.db.get_value("Custom Field", "Event-test_custom_field", "no_copy"), 0)

	def test_save_customization_new_field(self):
		d = self.get_customize_form("Event")
		last_fieldname = d.fields[-1].fieldname
		d.append(
			"fields",
			{
				"label": "Test Add Custom Field Via Customize Form",
				"fieldtype": "Data",
				"is_custom_field": 1,
			},
		)
		d.run_method("save_customization")
		self.assertEqual(
			frappe.db.get_value(
				"Custom Field", "Event-test_add_custom_field_via_customize_form", "fieldtype"
			),
			"Data",
		)

		self.assertEqual(
			frappe.db.get_value(
				"Custom Field", "Event-test_add_custom_field_via_customize_form", "insert_after"
			),
			last_fieldname,
		)

		frappe.delete_doc("Custom Field", "Event-test_add_custom_field_via_customize_form")
		self.assertEqual(
			frappe.db.get_value("Custom Field", "Event-test_add_custom_field_via_customize_form"), None
		)

	def test_save_customization_remove_field(self):
		d = self.get_customize_form("Event")
		custom_field = d.get("fields", {"fieldname": "test_custom_field"})[0]
		d.get("fields").remove(custom_field)
		d.run_method("save_customization")

		self.assertEqual(frappe.db.get_value("Custom Field", custom_field.name), None)

		frappe.local.test_objects["Custom Field"] = []
		make_test_records_for_doctype("Custom Field")

	def test_reset_to_defaults(self):
		d = frappe.get_doc("Customize Form")
		d.doc_type = "Event"
		d.run_method("reset_to_defaults")

		self.assertEqual(d.get("fields", {"fieldname": "repeat_this_event"})[0].in_list_view, 0)

		frappe.local.test_objects["Property Setter"] = []
		make_test_records_for_doctype("Property Setter")

	def test_set_allow_on_submit(self):
		d = self.get_customize_form("Event")
		d.get("fields", {"fieldname": "subject"})[0].allow_on_submit = 1
		d.get("fields", {"fieldname": "test_custom_field"})[0].allow_on_submit = 1
		d.run_method("save_customization")

		d = self.get_customize_form("Event")

		# don't allow for standard fields
		self.assertEqual(d.get("fields", {"fieldname": "subject"})[0].allow_on_submit or 0, 0)

		# allow for custom field
		self.assertEqual(d.get("fields", {"fieldname": "test_custom_field"})[0].allow_on_submit, 1)

	def test_title_field_pattern(self):
		d = self.get_customize_form("Web Form")

		df = d.get("fields", {"fieldname": "title"})[0]

		# invalid fieldname
		df.default = """{doc_type} - {introduction_test}"""
		self.assertRaises(InvalidFieldNameError, d.run_method, "save_customization")

		# space in formatter
		df.default = """{doc_type} - {introduction text}"""
		self.assertRaises(InvalidFieldNameError, d.run_method, "save_customization")

		# valid fieldname
		df.default = """{doc_type} - {introduction_text}"""
		d.run_method("save_customization")

		# valid fieldname with escaped curlies
		df.default = """{{ {doc_type} }} - {introduction_text}"""
		d.run_method("save_customization")

		# undo
		df.default = None
		d.run_method("save_customization")

	def test_core_doctype_customization(self):
		self.assertRaises(frappe.ValidationError, self.get_customize_form, "User")

	def test_save_customization_length_field_property(self):
		# Using Notification Log doctype as it doesn't have any other custom fields
		d = self.get_customize_form("Notification Log")

		document_name = d.get("fields", {"fieldname": "document_name"})[0]
		document_name.length = 255
		d.run_method("save_customization")

		self.assertEqual(
			frappe.db.get_value(
				"Property Setter",
				{"doc_type": "Notification Log", "property": "length", "field_name": "document_name"},
				"value",
			),
			"255",
		)

		self.assertTrue(d.flags.update_db)

		length = frappe.db.sql(
			"""SELECT character_maximum_length
			FROM information_schema.columns
			WHERE table_name = 'tabNotification Log'
			AND column_name = 'document_name'"""
		)[0][0]

		self.assertEqual(length, 255)

	def test_custom_link(self):
		try:
			# create a dummy doctype linked to Event
			testdt_name = "Test Link for Event"
			testdt = new_doctype(
				testdt_name, fields=[dict(fieldtype="Link", fieldname="event", options="Event")]
			).insert()

			testdt_name1 = "Test Link for Event 1"
			testdt1 = new_doctype(
				testdt_name1, fields=[dict(fieldtype="Link", fieldname="event", options="Event")]
			).insert()

			# add a custom link
			d = self.get_customize_form("Event")

			d.append("links", dict(link_doctype=testdt_name, link_fieldname="event", group="Tests"))
			d.append("links", dict(link_doctype=testdt_name1, link_fieldname="event", group="Tests"))

			d.run_method("save_customization")

			frappe.clear_cache()
			event = frappe.get_meta("Event")

			# check links exist
			self.assertTrue([d.name for d in event.links if d.link_doctype == testdt_name])
			self.assertTrue([d.name for d in event.links if d.link_doctype == testdt_name1])

			# check order
			order = json.loads(event.links_order)
			self.assertListEqual(order, [d.name for d in event.links])

			# remove the link
			d = self.get_customize_form("Event")
			d.links = []
			d.run_method("save_customization")

			frappe.clear_cache()
			event = frappe.get_meta("Event")
			self.assertFalse([d.name for d in (event.links or []) if d.link_doctype == testdt_name])
		finally:
			testdt.delete()
			testdt1.delete()

	def test_custom_internal_links(self):
		# add a custom internal link
		frappe.clear_cache()
		d = self.get_customize_form("User Group")

		d.append(
			"links",
			dict(
				link_doctype="User Group Member",
				parent_doctype="User Group",
				link_fieldname="user",
				table_fieldname="user_group_members",
				group="Tests",
				custom=1,
			),
		)

		d.run_method("save_customization")

		frappe.clear_cache()
		user_group = frappe.get_meta("User Group")

		# check links exist
		self.assertTrue([d.name for d in user_group.links if d.link_doctype == "User Group Member"])
		self.assertTrue([d.name for d in user_group.links if d.parent_doctype == "User Group"])

		# remove the link
		d = self.get_customize_form("User Group")
		d.links = []
		d.run_method("save_customization")

		frappe.clear_cache()
		user_group = frappe.get_meta("Event")
		self.assertFalse(
			[d.name for d in (user_group.links or []) if d.link_doctype == "User Group Member"]
		)

	def test_custom_action(self):
		test_route = "/app/List/DocType"

		# create a dummy action (route)
		d = self.get_customize_form("Event")
		d.append("actions", dict(label="Test Action", action_type="Route", action=test_route))
		d.run_method("save_customization")

		frappe.clear_cache()
		event = frappe.get_meta("Event")

		# check if added to meta
		action = [d for d in event.actions if d.label == "Test Action"]
		self.assertEqual(len(action), 1)
		self.assertEqual(action[0].action, test_route)

		# clear the action
		d = self.get_customize_form("Event")
		d.actions = []
		d.run_method("save_customization")

		frappe.clear_cache()
		event = frappe.get_meta("Event")

		action = [d for d in event.actions if d.label == "Test Action"]
		self.assertEqual(len(action), 0)

	def test_custom_label(self):
		d = self.get_customize_form("Event")

		# add label
		d.label = "Test Rename"
		d.run_method("save_customization")
		self.assertEqual(d.label, "Test Rename")

		# change label
		d.label = "Test Rename 2"
		d.run_method("save_customization")
		self.assertEqual(d.label, "Test Rename 2")

		# saving again to make sure existing label persists
		d.run_method("save_customization")
		self.assertEqual(d.label, "Test Rename 2")

		# clear label
		d.label = ""
		d.run_method("save_customization")
		self.assertEqual(d.label, "")

	def test_change_to_autoincrement_autoname(self):
		d = self.get_customize_form("Event")
		d.autoname = "autoincrement"

		with self.assertRaises(frappe.ValidationError):
			d.run_method("save_customization")

	def test_customized_field_order(self):
		def shuffle_fields():
			import random

			customized_form = self.get_customize_form(doctype="ToDo")
			random.shuffle(customized_form.fields)
			customized_form.save_customization()

		shuffle_fields()

		property_setter_field_order = json.loads(frappe.get_last_doc("Property Setter").value)
		set_field_order = self.get_customize_form(doctype="ToDo").fields

		for idx, field in enumerate(set_field_order, 0):
			self.assertEqual(field.fieldname, property_setter_field_order[idx])

	def test_customized_field_order_greater_than_insert_after(self):
		reset_customization(doctype="ToDo")
		frappe.delete_doc_if_exists("Custom Field", "ToDo-test_todo_type", force=True)
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "ToDo",
				"label": "Test ToDo Type",
				"description": "A Custom Field for Testing",
				"fieldtype": "Select",
				"in_list_view": 1,
				"options": "\nCustom 1\nCustom 2\nCustom 3",
				"default": "Custom 3",
				"insert_after": "description_section",
				"is_system_generated": 1,
			}
		).insert()

		customize_form = self.get_customize_form(doctype="ToDo")
		test_position = [f.fieldname for f in customize_form.fields].index("test_todo_type")
		self.assertEqual(customize_form.fields[test_position - 1].fieldname, "description_section")

		# Modify position of system generated field then test it is in its correct position.
		customize_form.fields.insert(1, customize_form.fields.pop(test_position))
		customize_form.save_customization()
		frappe.clear_cache(doctype="ToDo")

		customize_form = self.get_customize_form(doctype="ToDo")
		self.assertEqual(customize_form.fields[1].fieldname, "test_todo_type")

	def test_migrated_standard_field_order(self):
		frappe.db.delete("Custom Field", filters={"dt": "ToDo"})
		frappe.db.delete("Property Setter", filters={"doc_type": "ToDo"})

		# Revert new standard field test_new_standard_field if re-run.
		doctype = frappe.get_doc("DocType", "ToDo")
		doctype.fields.sort(key=lambda f: f.idx)
		if "test_new_standard_field" in [f.fieldname for f in doctype.fields]:
			position = [f.fieldname for f in doctype.fields].index("test_new_standard_field")
			for field in doctype.fields[position:]:
				if field.fieldname == "test_new_standard_field":
					frappe.db.delete("DocField", filters={"name": field.name})
				else:
					field.idx = field.idx - 1
					field.db_update()

		frappe.clear_cache(doctype="ToDo")

		# Move description field to top of form.
		customize_form = self.get_customize_form("ToDo")
		fields = [f.fieldname for f in customize_form.fields]
		description = customize_form.fields.pop(fields.index("description"))
		customize_form.fields.insert(1, description)
		customize_form.save_customization()

		# Create a new standard field under "Description"
		doctype = frappe.get_doc("DocType", "ToDo")

		# Shift standard field indexes after description up.
		doctype.fields.sort(key=lambda f: f.idx)
		position_description = [f.fieldname for f in doctype.fields].index("description")
		for field in doctype.fields[position_description + 1 :]:
			field.idx = field.idx + 1
			field.db_update()

		# Insert the new standard field after description.
		new_standard_field = doctype.append(
			"fields",
			{
				"fieldname": "test_new_standard_field",
				"label": "Test new standared field",
				"fieldtype": "Data",
				"idx": position_description + 2,
			},
		)
		new_standard_field.db_insert()

		# Test that my_test_field is ordered after description
		frappe.clear_cache(doctype="ToDo")
		customize_form = self.get_customize_form("ToDo")
		fields = [f.fieldname for f in customize_form.fields]
		self.assertEqual(fields[fields.index("description") + 1], "test_new_standard_field")
