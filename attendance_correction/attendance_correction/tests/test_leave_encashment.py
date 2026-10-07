"""
Leave Allocation -> Leave Encashment tests. Everything runs inside a transaction that is
rolled back, so no test data is left in the site.

Run:  bench --site testighr.com execute \
        attendance_correction.attendance_correction.tests.test_leave_encashment.run
"""
import unittest

import frappe
from frappe.utils import add_days, flt, getdate

from attendance_correction.attendance_correction.overrides.leave_encashment import (
	create_encashments_from_allocations,
	get_leave_allocation_summary,
)

EMPLOYEE = "6460"
TYPE_A, TYPE_B, TYPE_NO = "ZZ Test Encash A", "ZZ Test Encash B", "ZZ Test No Encash"
DATE = getdate("2026-09-30")


def make_leave_type(name, encashable=1, **kw):
	frappe.get_doc(
		dict(doctype="Leave Type", leave_type_name=name, allow_encashment=encashable, **kw)
	).insert(ignore_permissions=True)


def make_allocation(leave_type, from_date, to_date, days, submit=True):
	doc = frappe.get_doc(
		dict(
			doctype="Leave Allocation",
			employee=EMPLOYEE,
			leave_type=leave_type,
			from_date=from_date,
			to_date=to_date,
			new_leaves_allocated=days,
		)
	).insert(ignore_permissions=True)
	if submit:
		doc.submit()
	return doc


def make_encashment(leave_type, days=0, date=DATE):
	return frappe.get_doc(
		dict(
			doctype="Leave Encashment",
			employee=EMPLOYEE,
			leave_type=leave_type,
			encashment_date=date,
			encashment_days=days,
			pay_via_payment_entry=1,  # no Salary Structure Assignment in this site
		)
	)


class TestLeaveAllocationToEncashment(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("t")
		self.ctc = flt(frappe.db.get_value("Employee", EMPLOYEE, "ctc"))
		self.assertGreater(self.ctc, 0, "test employee needs CTC")
		self.company = frappe.db.get_value("Employee", EMPLOYEE, "company")
		self.ensure_leave_period("2025-01-01", "2026-12-31", DATE)
		make_leave_type(TYPE_A)
		make_leave_type(TYPE_B)
		make_leave_type(TYPE_NO, encashable=0)

	def ensure_leave_period(self, from_date, to_date, covering):
		# the site may already hold a Leave Period; periods of one company cannot overlap
		if not frappe.db.exists(
			"Leave Period",
			{"company": self.company, "is_active": 1, "from_date": ["<=", covering], "to_date": [">=", covering]},
		):
			frappe.get_doc(
				dict(doctype="Leave Period", from_date=from_date, to_date=to_date, is_active=1, company=self.company)
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback(save_point="t")

	def test_basic_balance_and_amount(self):
		a = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 20)
		enc = make_encashment(TYPE_A)
		enc.insert()
		self.assertEqual(enc.leave_allocation, a.name)
		self.assertTrue(enc.leave_period)
		self.assertEqual(enc.leave_balance, 20)
		self.assertEqual(enc.actual_encashable_days, 20)
		self.assertEqual(enc.encashment_days, 20)
		self.assertAlmostEqual(enc.encashment_amount, round(self.ctc / 30 * 20, 2), places=2)

	def test_encashment_days_cannot_be_overridden(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		for days in (4, 11):  # encashment days are always the full encashable balance
			enc = make_encashment(TYPE_A, days=days)
			enc.insert()
			self.assertEqual(enc.encashment_days, 10)
			self.assertAlmostEqual(enc.encashment_amount, round(self.ctc / 30 * 10, 2), places=2)
			enc.delete()

	def test_allocation_change_is_reflected(self):
		a = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		enc = make_encashment(TYPE_A)
		enc.insert()
		self.assertEqual(enc.leave_balance, 10)
		a.cancel()
		a2 = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 15)
		enc.reload()  # the draft is refreshed automatically when the allocation changes
		self.assertEqual(enc.leave_allocation, a2.name)
		self.assertEqual(enc.leave_balance, 15)

	def test_draft_follows_allocation_changes(self):
		a = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		enc = make_encashment(TYPE_A)
		enc.insert()
		self.assertEqual(enc.encashment_days, 10)

		# increase: amend the submitted allocation
		a.reload()
		a.new_leaves_allocated = 15
		a.save()  # on_update_after_submit
		enc.reload()
		self.assertEqual((enc.leave_balance, enc.encashment_days), (15, 15))
		self.assertAlmostEqual(enc.encashment_amount, round(self.ctc / 30 * 15, 2), places=2)

		# decrease via a new allocation after cancelling the old one
		a.cancel()
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 6)
		enc.reload()
		self.assertEqual((enc.leave_balance, enc.encashment_days), (6, 6))

	def test_employee_name_is_editable(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		enc = make_encashment(TYPE_A)
		enc.employee_name = "Custom Name"
		enc.insert()
		self.assertEqual(enc.employee_name, "Custom Name")
		enc.employee_name = "Other Name"
		enc.save()
		enc.reload()
		self.assertEqual(enc.employee_name, "Other Name")

	def test_cancelled_and_draft_allocation_ignored(self):
		a = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		a.cancel()
		with self.assertRaises(frappe.ValidationError):  # missing allocation
			make_encashment(TYPE_A).insert()
		make_allocation(TYPE_B, "2026-01-01", "2026-12-31", 10, submit=False)  # draft
		with self.assertRaises(frappe.ValidationError):
			make_encashment(TYPE_B).insert()
		self.assertEqual(get_leave_allocation_summary(EMPLOYEE, encashment_date=DATE), self._only(TYPE_A, TYPE_B, none=True))

	def _only(self, *types, none=False):
		# summary rows for the temporary types must be absent
		rows = [r for r in get_leave_allocation_summary(EMPLOYEE, encashment_date=DATE) if r["leave_type"] in types]
		self.assertEqual(rows, [])
		return get_leave_allocation_summary(EMPLOYEE, encashment_date=DATE)

	def test_multiple_allocations_pick_period_covering_date(self):
		self.ensure_leave_period("2025-01-01", "2025-12-31", "2025-06-01")
		old = make_allocation(TYPE_A, "2025-01-01", "2025-12-31", 7)
		cur = make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 12)
		self.assertEqual(make_encashment(TYPE_A, date="2025-06-01").insert().leave_allocation, old.name)
		self.assertEqual(make_encashment(TYPE_A, date=DATE).insert().leave_allocation, cur.name)

	def test_multiple_leave_types_in_summary(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 5)
		make_allocation(TYPE_B, "2026-01-01", "2026-12-31", 8)
		rows = {r["leave_type"]: r for r in get_leave_allocation_summary(EMPLOYEE, encashment_date=DATE)}
		self.assertEqual(rows[TYPE_A]["encashment_days"], 5)
		self.assertEqual(rows[TYPE_B]["encashment_days"], 8)
		self.assertAlmostEqual(rows[TYPE_B]["encashment_amount"], round(self.ctc / 30 * 8, 2), places=2)
		self.assertNotIn(TYPE_NO, rows)

	def test_non_encashable_type_rejected(self):
		make_allocation(TYPE_NO, "2026-01-01", "2026-12-31", 5)
		with self.assertRaises(frappe.ValidationError):
			make_encashment(TYPE_NO).insert()

	def test_zero_balance_cannot_submit(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 3)
		# consume the whole balance via a submitted ledger entry (as a Leave Application would)
		frappe.get_doc(
			dict(doctype="Leave Ledger Entry", employee=EMPLOYEE, leave_type=TYPE_A, leaves=-3,
				from_date="2026-09-01", to_date="2026-09-01", transaction_type="Leave Encashment",
				transaction_name="dummy")
		).insert(ignore_permissions=True, ignore_links=True).submit()
		enc = make_encashment(TYPE_A)
		enc.insert()
		self.assertEqual((enc.leave_balance, enc.encashment_days, enc.encashment_amount), (0, 0, 0))
		with self.assertRaises(frappe.ValidationError):
			enc.submit()

	def test_type_limits_and_leave_taken(self):
		frappe.db.set_value("Leave Type", TYPE_A, {"non_encashable_leaves": 2, "max_encashable_leaves": 6})
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 20)
		enc = make_encashment(TYPE_A)
		enc.insert()
		self.assertEqual(enc.leave_balance, 20)
		self.assertEqual(enc.actual_encashable_days, 6)  # min(20-2, 6)
		row = get_leave_allocation_summary(EMPLOYEE, TYPE_A, DATE)[0]
		self.assertEqual((row["leave_balance"], row["actual_encashable_days"]), (20, 6))

	def test_duplicate_draft_blocked(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		make_encashment(TYPE_A, days=2).insert()
		with self.assertRaises(frappe.ValidationError):
			make_encashment(TYPE_A, days=3).insert()

	def test_summary_matches_document_and_missing_type_raises(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 9)
		row = get_leave_allocation_summary(EMPLOYEE, TYPE_A, DATE)[0]
		enc = make_encashment(TYPE_A)
		enc.insert()
		for f in ("leave_balance", "actual_encashable_days", "encashment_days", "encashment_amount"):
			self.assertEqual(row[f], enc.get(f), f)
		with self.assertRaises(frappe.ValidationError):
			get_leave_allocation_summary(EMPLOYEE, TYPE_B, DATE)

	def test_status_paid_unpaid(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		enc = make_encashment(TYPE_A, days=3)
		enc.insert()
		self.assertEqual(enc.status, "Unpaid")  # draft, nothing paid
		enc.paid_amount = enc.encashment_amount
		enc.set_status()
		self.assertEqual(enc.status, "Paid")
		enc.paid_amount = enc.encashment_amount - 1
		enc.set_status()
		self.assertEqual(enc.status, "Unpaid")
		enc.docstatus = 2
		enc.set_status()
		self.assertEqual(enc.status, "Cancelled")

	def test_amount_follows_current_ctc(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 10)
		enc = make_encashment(TYPE_A)
		enc.insert()
		frappe.db.set_value("Employee", EMPLOYEE, "ctc", 60000)
		enc.save()
		self.assertEqual(enc.encashment_amount, 20000)  # 60000 / 30 * 10

	def test_bulk_create_from_allocations(self):
		make_allocation(TYPE_A, "2026-01-01", "2026-12-31", 8)
		make_allocation(TYPE_NO, "2026-01-01", "2026-12-31", 5)
		res = create_encashments_from_allocations(EMPLOYEE)
		mine = [n for n in res["created"] if frappe.db.get_value("Leave Encashment", n, "leave_type") == TYPE_A]
		self.assertEqual(len(mine), 1)
		enc = frappe.get_doc("Leave Encashment", mine[0])
		self.assertEqual((enc.docstatus, enc.leave_balance, enc.encashment_days), (0, 8, 8))
		self.assertAlmostEqual(enc.encashment_amount, round(self.ctc / 30 * 8, 2), places=2)
		self.assertEqual(enc.status, "Unpaid")
		reasons = {s["reason"] for s in res["skipped"]}
		self.assertIn("Leave Type is not encashable", reasons)
		# second run creates nothing new for the same allocations
		again = create_encashments_from_allocations(EMPLOYEE)
		self.assertEqual(again["created"], [])


def run():
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestLeaveAllocationToEncashment)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	frappe.db.rollback()
	if not result.wasSuccessful():
		raise SystemExit(1)
