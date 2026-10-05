import frappe
from frappe import _
from frappe.utils import flt, getdate

from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period
from hrms.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment


# Company policy: Encashment Amount = (CTC / 30) x Encashment Days
DAYS_IN_MONTH = 30


class CustomLeaveEncashment(LeaveEncashment):
	def validate(self):
		super().validate()
		self.validate_duplicate_draft()

	def _validate_links(self):
		# Frappe validates links before validate(); a draft still pointing at an allocation that
		# was since cancelled would be rejected before set_leave_balance() can re-resolve it.
		if (
			self.docstatus == 0
			and self.leave_allocation
			and frappe.db.get_value("Leave Allocation", self.leave_allocation, "docstatus") != 1
		):
			self.leave_allocation = None

		# Employee Name is editable, but Frappe re-fetches it from the Employee on every save;
		# keep a hand-entered name unless the employee itself was changed.
		name = self.employee_name
		keep_name = bool(name) and (self.is_new() or not self.has_value_changed("employee"))
		super()._validate_links()
		if keep_name:
			self.employee_name = name

	def set_leave_balance(self):
		super().set_leave_balance()
		self.set_leave_period()

	def set_leave_period(self):
		"""Leave Period is mandatory on Leave Encashment but optional on Leave Allocation:
		take it from the allocation, else from an active Leave Period covering the date."""
		self.leave_period = frappe.db.get_value("Leave Allocation", self.leave_allocation, "leave_period")
		if not self.leave_period:
			company = frappe.db.get_value("Employee", self.employee, "company")
			self.leave_period = frappe.db.get_value(
				"Leave Period",
				{
					"is_active": 1,
					"company": company,
					"from_date": ["<=", self.encashment_date],
					"to_date": [">=", self.encashment_date],
				},
				"name",
			)

	def validate_duplicate_draft(self):
		"""One open (draft) encashment per employee + leave type + allocation, so two
		drafts cannot both be prepared against the same balance."""
		duplicate = frappe.db.exists(
			"Leave Encashment",
			{
				"employee": self.employee,
				"leave_type": self.leave_type,
				"leave_allocation": self.leave_allocation,
				"docstatus": 0,
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Draft Leave Encashment {0} already exists for {1} / {2} against {3}").format(
					frappe.utils.get_link_to_form("Leave Encashment", duplicate),
					self.employee,
					self.leave_type,
					self.leave_allocation,
				)
			)

	def set_encashment_days(self):
		"""Leave Balance, Actual Encashable Days and Encashment Days are read-only on the form and
		always come from the employee's Leave Allocation: the whole encashable balance is encashed,
		whatever value arrives from the client or an API caller."""
		self.encashment_days = self.actual_encashable_days

	def set_encashment_amount(self):
		"""
		Replaces the HRMS default (encashment_days x Salary Structure
		'leave_encashment_amount_per_day') with the CTC based formula.
		Called from validate() and from the form's live refresh.
		"""
		ctc = flt(frappe.db.get_value("Employee", self.employee, "ctc"))

		if ctc <= 0:
			frappe.msgprint(
				f"CTC is not set for Employee {self.employee}. "
				"Encashment Amount cannot be calculated.",
				indicator="orange",
				alert=True,
			)

		per_day = ctc / DAYS_IN_MONTH
		self.encashment_amount = flt(
			per_day * flt(self.encashment_days), self.precision("encashment_amount")
		)

	def set_status(self, update=False):
		"""Status is Paid / Unpaid (Cancelled once cancelled) instead of HRMS's Draft.

		Paid means the amount is covered: by paid_amount (Payment Entry route), or, on the
		Additional Salary route, HRMS flags it Paid when the Salary Slip is submitted."""
		if self.docstatus == 2:
			status = "Cancelled"
		else:
			precision = self.precision("paid_amount")
			amount = flt(self.encashment_amount)
			status = "Paid" if amount > 0 and flt(self.paid_amount, precision) >= amount else "Unpaid"

		if update:
			self.db_set("status", status)
			self.notify_update()
		else:
			self.status = status


@frappe.whitelist()
def get_leave_allocation_summary(employee, leave_type=None, encashment_date=None):
	"""
	Leave Allocation -> Leave Encashment breakdown for an employee, one row per
	encashable Leave Type that has a submitted Leave Allocation covering `encashment_date`
	(default today). Cancelled/draft allocations are ignored.

	Uses the same controller methods as the Leave Encashment form, so the numbers here
	always equal what a Leave Encashment created for the same inputs will show:

	  leave_balance   = total_leaves_allocated - carry_forwarded_leaves_count
	                    - leaves taken/encashed up to encashment_date (Leave Ledger Entry)
	  encashable_days = leave_balance, less Leave Type non_encashable_leaves, capped at
	                    max_encashable_leaves
	  amount          = CTC / 30 x encashment_days   (encashment_days defaults to encashable_days)
	"""
	frappe.has_permission("Leave Allocation", "read", throw=True)
	encashment_date = getdate(encashment_date) if encashment_date else getdate()

	leave_types = [leave_type] if leave_type else frappe.get_all(
		"Leave Type", filters={"allow_encashment": 1}, pluck="name"
	)

	rows = []
	for lt in leave_types:
		doc = frappe.new_doc("Leave Encashment")
		doc.employee, doc.leave_type, doc.encashment_date = employee, lt, encashment_date

		allocation = doc.get_leave_allocation()
		if not allocation:
			if leave_type:
				frappe.throw(_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(employee, lt))
			continue

		# the controller msgprints Leave Type limits; keep those out of API callers' UI
		log = list(frappe.local.message_log)
		try:
			doc.set_leave_balance()
			doc.set_actual_encashable_days()
			doc.set_encashment_days()
			doc.set_encashment_amount()
		finally:
			frappe.local.message_log = log

		used = -flt(get_leaves_for_period(employee, lt, allocation.from_date, encashment_date))
		rows.append(
			{
				"leave_type": lt,
				"leave_allocation": allocation.name,
				"from_date": allocation.from_date,
				"to_date": allocation.to_date,
				"total_leaves_allocated": flt(allocation.total_leaves_allocated),
				"carry_forwarded_leaves_count": flt(allocation.carry_forwarded_leaves_count),
				"leaves_used_or_encashed": used,
				"leave_balance": flt(doc.leave_balance),
				"actual_encashable_days": flt(doc.actual_encashable_days),
				"encashment_days": flt(doc.encashment_days),
				"encashment_amount": flt(doc.encashment_amount),
			}
		)
	return rows


@frappe.whitelist()
def create_encashments_from_allocations(employee=None, leave_type=None, encashment_date=None):
	"""
	Shift Leave Allocation records into Leave Encashment: one draft Leave Encashment for every
	submitted Leave Allocation of an encashable Leave Type (optionally only one employee /
	leave type). Balance, encashable days, encashment days, amount and leave period are filled by
	CustomLeaveEncashment, exactly as when the form is saved.

	encashment_date defaults to today, moved inside the allocation's period if today falls outside it.
	Allocations that already have a non-cancelled Leave Encashment are skipped, so it is safe to
	run again. Returns {"created": [...], "skipped": [{"leave_allocation", "reason"}]}.
	"""
	frappe.has_permission("Leave Encashment", "create", throw=True)

	filters = {"docstatus": 1}
	if employee:
		filters["employee"] = employee
	if leave_type:
		filters["leave_type"] = leave_type

	created, skipped = [], []
	for alloc in frappe.get_all(
		"Leave Allocation",
		filters=filters,
		fields=["name", "employee", "leave_type", "from_date", "to_date"],
		order_by="from_date, name",
	):
		if not frappe.db.get_value("Leave Type", alloc.leave_type, "allow_encashment"):
			skipped.append({"leave_allocation": alloc.name, "reason": "Leave Type is not encashable"})
			continue

		if frappe.db.exists(
			"Leave Encashment",
			{"leave_allocation": alloc.name, "docstatus": ["<", 2]},
		):
			skipped.append({"leave_allocation": alloc.name, "reason": "Leave Encashment already exists"})
			continue

		date = getdate(encashment_date) if encashment_date else getdate()
		date = min(max(date, getdate(alloc.from_date)), getdate(alloc.to_date))

		savepoint = "encash_" + alloc.name.replace("-", "_")
		frappe.db.savepoint(savepoint)
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Leave Encashment",
					"employee": alloc.employee,
					"leave_type": alloc.leave_type,
					"encashment_date": date,
					"pay_via_payment_entry": 1,
				}
			).insert()
			created.append(doc.name)
		except Exception as e:
			frappe.db.rollback(save_point=savepoint)
			skipped.append({"leave_allocation": alloc.name, "reason": frappe.utils.strip_html(str(e))})

	return {"created": created, "skipped": skipped}


def refresh_draft_encashments(employee, leave_type=None):
	"""Re-save the employee's draft Leave Encashments so balance, encashable days, encashment days
	and amount follow the current Leave Allocation / Leave Ledger. Submitted ones are history and
	are never touched. A failure on one draft is logged and does not block the others."""
	filters = {"employee": employee, "docstatus": 0}
	if leave_type:
		filters["leave_type"] = leave_type

	for name in frappe.get_all("Leave Encashment", filters=filters, pluck="name"):
		savepoint = "refresh_" + name.replace("-", "_")
		frappe.db.savepoint(savepoint)
		try:
			doc = frappe.get_doc("Leave Encashment", name)
			doc.flags.ignore_permissions = True
			doc.save()
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(
				title=f"Could not refresh draft Leave Encashment {name}", message=frappe.get_traceback()
			)


def sync_on_leave_change(doc, method=None):
	"""doc_events handler for Leave Allocation and Leave Application: any submit, cancel or
	amendment changes the balance, so the employee's draft encashments are recalculated."""
	if doc.get("employee") and doc.get("leave_type"):
		refresh_draft_encashments(doc.employee, doc.leave_type)
